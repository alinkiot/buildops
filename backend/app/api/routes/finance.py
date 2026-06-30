"""财税账本：收支流水、发票登记、无票标记、风险扫描(R-004)、项目利润表。"""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ensure_project_visible, get_current_user, require_permission, write_audit
from app.db.session import get_db
from app.models import Alert, FinanceRecord, Project, User
from app.models.enums import AlertLevel, AlertSource, AlertStatus, FinanceDirection, FinanceStatus
from app.schemas.common import ApiResponse, PageResult, ok
from app.schemas.models import (
    FinanceRecordCreate,
    FinanceRecordOut,
    FinanceRecordUpdate,
    FinanceScanResult,
    ProfitStatement,
)

router = APIRouter(prefix="/finance", tags=["财税账本"])

NO_INVOICE_THRESHOLD = 0.10  # 无票支出占比预警阈值 10%
_COUNTED = (FinanceStatus.PENDING, FinanceStatus.POSTED, FinanceStatus.PENDING_INVOICE, FinanceStatus.ABNORMAL)


def _check_project(db: Session, user: User, project_id: int) -> Project:
    proj = db.get(Project, project_id)
    if not proj or proj.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="项目不存在")
    if not ensure_project_visible(user, project_id):
        raise HTTPException(403, detail="无权访问该项目（未授权）")
    return proj


@router.get("", response_model=ApiResponse[PageResult[FinanceRecordOut]])
def list_records(
    project_id: int = Query(...),
    direction: FinanceDirection | None = Query(None),
    status: FinanceStatus | None = Query(None),
    has_invoice: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_project(db, user, project_id)
    stmt = select(FinanceRecord).where(FinanceRecord.tenant_id == user.tenant_id, FinanceRecord.project_id == project_id)
    if direction:
        stmt = stmt.where(FinanceRecord.direction == direction)
    if status:
        stmt = stmt.where(FinanceRecord.status == status)
    if has_invoice is not None:
        stmt = stmt.where(FinanceRecord.has_invoice.is_(has_invoice))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(FinanceRecord.record_date.desc().nulls_last(), FinanceRecord.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return ok(PageResult[FinanceRecordOut](
        items=[FinanceRecordOut.model_validate(r) for r in rows], page=page, page_size=page_size, total=total
    ))


@router.post("", response_model=ApiResponse[FinanceRecordOut])
def create_record(
    payload: FinanceRecordCreate,
    user: User = Depends(require_permission("finance:manage")),
    db: Session = Depends(get_db),
):
    _check_project(db, user, payload.project_id)
    amount = Decimal(str(payload.amount))
    tax_rate = Decimal(str(payload.tax_rate))
    tax_amount = Decimal(str(payload.tax_amount)) if payload.tax_amount is not None else (amount * tax_rate).quantize(Decimal("0.01"))

    rec = FinanceRecord(
        tenant_id=user.tenant_id,
        project_id=payload.project_id,
        direction=payload.direction,
        category=payload.category,
        amount=amount,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        has_invoice=payload.has_invoice,
        invoice_no=payload.invoice_no,
        counterparty=payload.counterparty,
        record_date=payload.record_date,
        status=payload.status,
        remark=payload.remark,
    )
    if payload.direction == FinanceDirection.EXPENSE and not payload.has_invoice:
        rec.risk_tag = "无票"
    db.add(rec)
    db.commit()
    db.refresh(rec)
    write_audit(db, user=user, action="create", target_type="finance_record", target_id=rec.id)
    return ok(FinanceRecordOut.model_validate(rec))


@router.put("/{rid}", response_model=ApiResponse[FinanceRecordOut])
def update_record(
    rid: int,
    payload: FinanceRecordUpdate,
    user: User = Depends(require_permission("finance:manage")),
    db: Session = Depends(get_db),
):
    rec = db.get(FinanceRecord, rid)
    if not rec or rec.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="流水不存在")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(rec, k, v)
    # 税额联动：金额或税率变化且未显式传税额时重算
    if ("amount" in data or "tax_rate" in data) and "tax_amount" not in data:
        rec.tax_amount = (Decimal(str(rec.amount)) * Decimal(str(rec.tax_rate))).quantize(Decimal("0.01"))
    if rec.has_invoice and rec.risk_tag == "无票":
        rec.risk_tag = None
    db.commit()
    db.refresh(rec)
    write_audit(db, user=user, action="update", target_type="finance_record", target_id=rec.id)
    return ok(FinanceRecordOut.model_validate(rec))


@router.delete("/{rid}", response_model=ApiResponse[dict])
def delete_record(
    rid: int,
    user: User = Depends(require_permission("finance:manage")),
    db: Session = Depends(get_db),
):
    rec = db.get(FinanceRecord, rid)
    if not rec or rec.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="流水不存在")
    db.delete(rec)
    db.commit()
    write_audit(db, user=user, action="delete", target_type="finance_record", target_id=rid)
    return ok({"success": True})


# ---------------- 财税风险扫描（R-004） ----------------
@router.post("/scan", response_model=ApiResponse[FinanceScanResult])
def scan_risk(
    project_id: int = Query(...),
    user: User = Depends(require_permission("finance:manage")),
    db: Session = Depends(get_db),
):
    """扫描无票支出占比，超阈值生成财税风险预警并标记无票流水。"""
    proj = _check_project(db, user, project_id)
    expenses = db.execute(
        select(FinanceRecord).where(
            FinanceRecord.tenant_id == user.tenant_id,
            FinanceRecord.project_id == project_id,
            FinanceRecord.direction == FinanceDirection.EXPENSE,
            FinanceRecord.status.in_(_COUNTED),
        )
    ).scalars().all()

    total_expense = sum((Decimal(str(e.amount)) for e in expenses), Decimal("0"))
    no_invoice = sum((Decimal(str(e.amount)) for e in expenses if not e.has_invoice), Decimal("0"))
    ratio = float(no_invoice / total_expense) if total_expense else 0.0

    flagged = 0
    for e in expenses:
        if not e.has_invoice:
            if e.risk_tag != "无票" or e.status != FinanceStatus.PENDING_INVOICE:
                e.risk_tag = "无票"
                e.status = FinanceStatus.PENDING_INVOICE
                flagged += 1

    alerts = 0
    if ratio > NO_INVOICE_THRESHOLD:
        title = f"财税风险：无票支出占比 {ratio * 100:.1f}% 超过阈值 {NO_INVOICE_THRESHOLD * 100:.0f}%"
        dup = db.execute(
            select(Alert).where(
                Alert.tenant_id == user.tenant_id,
                Alert.source == AlertSource.FINANCE,
                Alert.project_id == project_id,
                Alert.title == title,
                Alert.status != AlertStatus.CLOSED,
            )
        ).scalars().first()
        if not dup:
            db.add(Alert(
                tenant_id=user.tenant_id,
                source=AlertSource.FINANCE,
                title=title,
                project_id=project_id,
                level=AlertLevel.HIGH,
                owner_id=proj.owner_id or user.id,
                status=AlertStatus.PENDING,
            ))
            alerts = 1

    db.commit()
    write_audit(db, user=user, action="scan", target_type="project", target_id=project_id,
                detail=f"no_invoice_ratio={ratio:.3f},flagged={flagged},alerts={alerts}")
    return ok(FinanceScanResult(
        scanned=len(expenses),
        no_invoice_expense=no_invoice,
        total_expense=total_expense,
        no_invoice_ratio=round(ratio * 100, 1),
        flagged=flagged,
        alerts_created=alerts,
    ))


# ---------------- 项目利润表 ----------------
@router.get("/profit", response_model=ApiResponse[ProfitStatement])
def profit_statement(
    project_id: int = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_project(db, user, project_id)
    records = db.execute(
        select(FinanceRecord).where(
            FinanceRecord.tenant_id == user.tenant_id,
            FinanceRecord.project_id == project_id,
            FinanceRecord.status.in_(_COUNTED),
        )
    ).scalars().all()

    income = sum((Decimal(str(r.amount)) for r in records if r.direction == FinanceDirection.INCOME), Decimal("0"))
    expense = sum((Decimal(str(r.amount)) for r in records if r.direction == FinanceDirection.EXPENSE), Decimal("0"))
    tax = sum((Decimal(str(r.tax_amount)) for r in records), Decimal("0"))
    invoiced_income = sum((Decimal(str(r.amount)) for r in records if r.direction == FinanceDirection.INCOME and r.has_invoice), Decimal("0"))
    no_invoice_expense = sum((Decimal(str(r.amount)) for r in records if r.direction == FinanceDirection.EXPENSE and not r.has_invoice), Decimal("0"))

    gross = income - expense
    net = income - expense - tax
    net_margin = float(net / income * 100) if income else 0.0
    no_invoice_ratio = float(no_invoice_expense / expense * 100) if expense else 0.0

    return ok(ProfitStatement(
        project_id=project_id,
        total_income=income,
        total_expense=expense,
        total_tax=tax,
        gross_profit=gross,
        net_profit=net,
        net_margin=round(net_margin, 1),
        invoiced_income=invoiced_income,
        no_invoice_expense=no_invoice_expense,
        no_invoice_ratio=round(no_invoice_ratio, 1),
    ))
