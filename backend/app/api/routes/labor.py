"""劳务法务：工人档案、工资发放、用工风险扫描(无合同/工伤保险缺失→高风险)、用工概览。"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission, write_audit
from app.db.session import get_db
from app.models import Alert, PayrollRecord, Project, Worker, User
from app.models.enums import AlertLevel, AlertSource, AlertStatus, WorkerStatus
from app.schemas.common import ApiResponse, PageResult, ok
from app.schemas.models import (
    LaborScanResult,
    LaborSummary,
    NameValue,
    PayrollCreate,
    PayrollOut,
    WorkerCreate,
    WorkerOut,
    WorkerUpdate,
)

router = APIRouter(prefix="/labor", tags=["劳务法务"])


def _get_worker(db: Session, user: User, wid: int) -> Worker:
    w = db.get(Worker, wid)
    if not w or w.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="工人不存在")
    return w


def _insurance_missing(w: Worker, today: date) -> bool:
    return w.insurance_expiry is None or w.insurance_expiry < today


# ---------------- 用工概览 ----------------
@router.get("/summary", response_model=ApiResponse[LaborSummary])
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    workers = db.execute(select(Worker).where(Worker.tenant_id == user.tenant_id)).scalars().all()
    onsite = [w for w in workers if w.status == WorkerStatus.ONSITE]
    contract_missing = sum(1 for w in onsite if not w.contract_signed)
    insurance_missing = sum(1 for w in onsite if _insurance_missing(w, today))
    risk_workers = sum(1 for w in workers if w.risk_tag)

    unpaid = db.execute(
        select(func.coalesce(func.sum(PayrollRecord.amount), 0)).where(
            PayrollRecord.tenant_id == user.tenant_id, PayrollRecord.paid.is_(False)
        )
    ).scalar_one()

    team_counter: dict = {}
    for w in onsite:
        key = w.team or "未分组"
        team_counter[key] = team_counter.get(key, 0) + 1
    by_team = [NameValue(name=k, value=v) for k, v in team_counter.items()]

    return ok(LaborSummary(
        total=len(workers), onsite=len(onsite), contract_missing=contract_missing,
        insurance_missing=insurance_missing, risk_workers=risk_workers,
        unpaid_amount=Decimal(str(unpaid)), by_team=by_team,
    ))


# ---------------- 用工风险扫描 ----------------
@router.post("/scan", response_model=ApiResponse[LaborScanResult])
def scan_risk(
    user: User = Depends(require_permission("labor:manage")),
    db: Session = Depends(get_db),
):
    """扫描在场工人：无劳动合同或工伤保险缺失/过期 → 标记高风险并生成预警。"""
    today = date.today()
    workers = db.execute(select(Worker).where(Worker.tenant_id == user.tenant_id)).scalars().all()
    contract_missing = insurance_missing = flagged = alerts = 0
    for w in workers:
        if w.status != WorkerStatus.ONSITE:
            if w.risk_tag:
                w.risk_tag = None
            continue
        issues = []
        if not w.contract_signed:
            issues.append("无劳动合同")
            contract_missing += 1
        if _insurance_missing(w, today):
            issues.append("工伤保险缺失/过期")
            insurance_missing += 1
        if issues:
            w.risk_tag = "、".join(issues)
            flagged += 1
            title = f"用工风险：{w.name}（{w.team or '-'}）{w.risk_tag}"
            dup = db.execute(
                select(Alert).where(
                    Alert.tenant_id == user.tenant_id,
                    Alert.source == AlertSource.LABOR,
                    Alert.title == title,
                    Alert.status != AlertStatus.CLOSED,
                )
            ).scalars().first()
            if not dup:
                db.add(Alert(
                    tenant_id=user.tenant_id,
                    source=AlertSource.LABOR,
                    title=title,
                    project_id=w.project_id,
                    level=AlertLevel.HIGH,
                    owner_id=w.owner_id or user.id,
                    status=AlertStatus.PENDING,
                ))
                alerts += 1
        elif w.risk_tag:
            w.risk_tag = None
    db.commit()
    write_audit(db, user=user, action="scan", target_type="worker",
                detail=f"contract_missing={contract_missing},insurance_missing={insurance_missing},alerts={alerts}")
    return ok(LaborScanResult(
        scanned=len(workers), contract_missing=contract_missing,
        insurance_missing=insurance_missing, flagged=flagged, alerts_created=alerts,
    ))


# ---------------- 工人档案 ----------------
@router.get("/workers", response_model=ApiResponse[PageResult[WorkerOut]])
def list_workers(
    project_id: int | None = Query(None),
    status: WorkerStatus | None = Query(None),
    team: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Worker).where(Worker.tenant_id == user.tenant_id)
    if project_id:
        stmt = stmt.where(Worker.project_id == project_id)
    if status:
        stmt = stmt.where(Worker.status == status)
    if team:
        stmt = stmt.where(Worker.team == team)
    if keyword:
        stmt = stmt.where(Worker.name.like(f"%{keyword}%"))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(Worker.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return ok(PageResult[WorkerOut](
        items=[WorkerOut.model_validate(r) for r in rows], page=page, page_size=page_size, total=total
    ))


@router.post("/workers", response_model=ApiResponse[WorkerOut])
def create_worker(
    payload: WorkerCreate,
    user: User = Depends(require_permission("labor:manage")),
    db: Session = Depends(get_db),
):
    if payload.project_id:
        proj = db.get(Project, payload.project_id)
        if not proj or proj.tenant_id != user.tenant_id:
            raise HTTPException(404, detail="项目不存在")
    w = Worker(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(w)
    db.commit()
    db.refresh(w)
    write_audit(db, user=user, action="create", target_type="worker", target_id=w.id)
    return ok(WorkerOut.model_validate(w))


@router.put("/workers/{wid}", response_model=ApiResponse[WorkerOut])
def update_worker(
    wid: int,
    payload: WorkerUpdate,
    user: User = Depends(require_permission("labor:manage")),
    db: Session = Depends(get_db),
):
    w = _get_worker(db, user, wid)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(w, k, v)
    db.commit()
    db.refresh(w)
    write_audit(db, user=user, action="update", target_type="worker", target_id=w.id)
    return ok(WorkerOut.model_validate(w))


@router.delete("/workers/{wid}", response_model=ApiResponse[dict])
def delete_worker(
    wid: int,
    user: User = Depends(require_permission("labor:manage")),
    db: Session = Depends(get_db),
):
    w = _get_worker(db, user, wid)
    db.delete(w)
    db.commit()
    write_audit(db, user=user, action="delete", target_type="worker", target_id=wid)
    return ok({"success": True})


# ---------------- 工资发放 ----------------
@router.get("/workers/{wid}/payroll", response_model=ApiResponse[list[PayrollOut]])
def list_payroll(wid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_worker(db, user, wid)
    rows = db.execute(
        select(PayrollRecord).where(PayrollRecord.worker_id == wid).order_by(PayrollRecord.id.desc())
    ).scalars().all()
    return ok([PayrollOut.model_validate(r) for r in rows])


@router.post("/workers/{wid}/payroll", response_model=ApiResponse[PayrollOut])
def add_payroll(
    wid: int,
    payload: PayrollCreate,
    user: User = Depends(require_permission("labor:manage")),
    db: Session = Depends(get_db),
):
    _get_worker(db, user, wid)
    rec = PayrollRecord(tenant_id=user.tenant_id, worker_id=wid, **payload.model_dump())
    db.add(rec)
    db.commit()
    db.refresh(rec)
    write_audit(db, user=user, action="payroll", target_type="worker", target_id=wid,
                detail=f"period={payload.period},amount={payload.amount}")
    return ok(PayrollOut.model_validate(rec))
