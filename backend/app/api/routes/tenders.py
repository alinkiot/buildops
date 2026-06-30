"""招投标：标讯/投标项目台账、资质准入校验(R-002)、保证金到期扫描、投标看板与中标率。"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission, write_audit
from app.db.session import get_db
from app.models import Alert, Qualification, Tender, User
from app.models.enums import (
    AlertLevel,
    AlertSource,
    AlertStatus,
    QualificationStatus,
    TenderStatus,
)
from app.schemas.common import ApiResponse, PageResult, ok
from app.schemas.models import (
    DepositScanResult,
    NameValue,
    TenderBoard,
    TenderCreate,
    TenderEvalResult,
    TenderOut,
    TenderUpdate,
)

router = APIRouter(prefix="/tenders", tags=["招投标"])

_STATUS_LABELS = {
    TenderStatus.PENDING_EVAL: "待评估", TenderStatus.CAN_BID: "可投", TenderStatus.CANNOT_BID: "不可投",
    TenderStatus.REGISTERING: "报名中", TenderStatus.PREPARING: "标书制作中", TenderStatus.BIDDED: "已投标",
    TenderStatus.WON: "已中标", TenderStatus.LOST: "未中标", TenderStatus.FAILED: "废标",
    TenderStatus.ARCHIVED: "归档",
}


def _get(db: Session, user: User, tid: int) -> Tender:
    t = db.get(Tender, tid)
    if not t or t.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="标讯不存在")
    return t


@router.get("", response_model=ApiResponse[PageResult[TenderOut]])
def list_tenders(
    status: TenderStatus | None = Query(None),
    region: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Tender).where(Tender.tenant_id == user.tenant_id)
    if status:
        stmt = stmt.where(Tender.status == status)
    if region:
        stmt = stmt.where(Tender.region == region)
    if keyword:
        stmt = stmt.where(Tender.name.like(f"%{keyword}%"))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(Tender.registration_deadline.asc().nulls_last(), Tender.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return ok(PageResult[TenderOut](
        items=[TenderOut.model_validate(r) for r in rows], page=page, page_size=page_size, total=total
    ))


@router.get("/board", response_model=ApiResponse[TenderBoard])
def board(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Tender).where(Tender.tenant_id == user.tenant_id)).scalars().all()
    counter: dict = {}
    for t in rows:
        counter[t.status] = counter.get(t.status, 0) + 1
    by_status = [NameValue(name=_STATUS_LABELS.get(st, str(st)), value=cnt) for st, cnt in counter.items()]

    won = counter.get(TenderStatus.WON, 0)
    lost = counter.get(TenderStatus.LOST, 0)
    submitted = counter.get(TenderStatus.BIDDED, 0)
    bidded = won + lost + submitted          # 有效投标项目数
    decided = won + lost
    win_rate = round(won / decided * 100, 1) if decided else 0.0

    deposit_out = sum(
        (Decimal(str(t.deposit_amount)) for t in rows if not t.deposit_returned and t.deposit_amount),
        Decimal("0"),
    )
    today = date.today()
    deposit_overdue = sum(
        1 for t in rows
        if not t.deposit_returned and t.deposit_amount and t.deposit_due and t.deposit_due < today
    )
    return ok(TenderBoard(
        total=len(rows), by_status=by_status, bidded=bidded, won=won, win_rate=win_rate,
        deposit_outstanding=deposit_out, deposit_overdue=deposit_overdue,
    ))


@router.get("/{tid}", response_model=ApiResponse[TenderOut])
def get_tender(tid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(TenderOut.model_validate(_get(db, user, tid)))


@router.post("", response_model=ApiResponse[TenderOut])
def create_tender(
    payload: TenderCreate,
    user: User = Depends(require_permission("tender:manage")),
    db: Session = Depends(get_db),
):
    t = Tender(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    write_audit(db, user=user, action="create", target_type="tender", target_id=t.id)
    return ok(TenderOut.model_validate(t))


@router.put("/{tid}", response_model=ApiResponse[TenderOut])
def update_tender(
    tid: int,
    payload: TenderUpdate,
    user: User = Depends(require_permission("tender:manage")),
    db: Session = Depends(get_db),
):
    t = _get(db, user, tid)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    write_audit(db, user=user, action="update", target_type="tender", target_id=t.id)
    return ok(TenderOut.model_validate(t))


@router.delete("/{tid}", response_model=ApiResponse[dict])
def delete_tender(
    tid: int,
    user: User = Depends(require_permission("tender:manage")),
    db: Session = Depends(get_db),
):
    t = _get(db, user, tid)
    db.delete(t)
    db.commit()
    write_audit(db, user=user, action="delete", target_type="tender", target_id=tid)
    return ok({"success": True})


def _split_reqs(text: str | None) -> list[str]:
    if not text:
        return []
    parts = re.split(r"[、,，;；/\s]+", text)
    return [p.strip() for p in parts if p.strip()]


# ---------------- 资质准入校验（R-002） ----------------
@router.post("/{tid}/evaluate", response_model=ApiResponse[TenderEvalResult])
def evaluate_tender(
    tid: int,
    user: User = Depends(require_permission("tender:manage")),
    db: Session = Depends(get_db),
):
    """根据企业有效资质校验投标准入；不满足则标记不可投并生成预警（R-002）。"""
    t = _get(db, user, tid)
    today = date.today()
    # 仅取仍在有效期内、未停用、未过期的资质
    quals = db.execute(
        select(Qualification).where(Qualification.tenant_id == user.tenant_id)
    ).scalars().all()
    valid_quals = [
        q for q in quals
        if q.status != QualificationStatus.DISABLED
        and (q.valid_to is None or q.valid_to >= today)
        and q.status != QualificationStatus.EXPIRED
    ]
    valid_names = " ".join((q.name or "") + " " + (q.scope or "") for q in valid_quals)

    reasons: list[str] = []
    for req in _split_reqs(t.qualification_req):
        if req not in valid_names:
            reasons.append(f"缺少满足『{req}』的有效资质")

    # 地域要求（信息性提示）
    if t.region_req and t.region and t.region_req not in (t.region or ""):
        # 仅当显式不一致时提示，宽松处理
        pass

    can_bid = len(reasons) == 0
    t.status = TenderStatus.CAN_BID if can_bid else TenderStatus.CANNOT_BID
    t.eval_reason = "资质满足，可投" if can_bid else "；".join(reasons)

    alerts_created = 0
    if not can_bid:
        title = f"投标准入不通过：『{t.name}』{t.eval_reason}"
        dup = db.execute(
            select(Alert).where(
                Alert.tenant_id == user.tenant_id,
                Alert.source == AlertSource.BID,
                Alert.title == title,
                Alert.status != AlertStatus.CLOSED,
            )
        ).scalars().first()
        if not dup:
            db.add(Alert(
                tenant_id=user.tenant_id,
                source=AlertSource.BID,
                title=title,
                level=AlertLevel.MEDIUM,
                owner_id=t.owner_id or user.id,
                due_date=t.registration_deadline,
                status=AlertStatus.PENDING,
            ))
            alerts_created = 1

    db.commit()
    write_audit(db, user=user, action="evaluate", target_type="tender", target_id=t.id,
                detail=f"can_bid={can_bid}")
    return ok(TenderEvalResult(can_bid=can_bid, reasons=reasons, status=t.status))


# ---------------- 保证金到期扫描 ----------------
@router.post("/scan-deposit", response_model=ApiResponse[DepositScanResult])
def scan_deposit(
    user: User = Depends(require_permission("tender:manage")),
    db: Session = Depends(get_db),
):
    today = date.today()
    rows = db.execute(select(Tender).where(Tender.tenant_id == user.tenant_id)).scalars().all()
    overdue = alerts = 0
    for t in rows:
        if t.deposit_returned or not t.deposit_amount or not t.deposit_due:
            continue
        if t.deposit_due < today:
            overdue += 1
            days = (today - t.deposit_due).days
            title = f"保证金逾期未退：『{t.name}』{Decimal(str(t.deposit_amount)):.2f} 元已逾期 {days} 天"
            dup = db.execute(
                select(Alert).where(
                    Alert.tenant_id == user.tenant_id,
                    Alert.source == AlertSource.BID,
                    Alert.title == title,
                    Alert.status != AlertStatus.CLOSED,
                )
            ).scalars().first()
            if not dup:
                db.add(Alert(
                    tenant_id=user.tenant_id,
                    source=AlertSource.BID,
                    title=title,
                    level=AlertLevel.HIGH,
                    owner_id=t.owner_id or user.id,
                    due_date=t.deposit_due,
                    status=AlertStatus.PENDING,
                ))
                alerts += 1
    db.commit()
    write_audit(db, user=user, action="scan", target_type="tender",
                detail=f"deposit_overdue={overdue},alerts={alerts}")
    return ok(DepositScanResult(scanned=len(rows), overdue=overdue, alerts_created=alerts))
