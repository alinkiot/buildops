"""回款清欠：债权台账、催收日志、回款登记(同步财税)、逾期分级扫描(R-006)、汇总与信用、文书生成。"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ensure_project_visible, get_current_user, require_permission, write_audit
from app.db.session import get_db
from app.models import (
    Alert,
    ClientUnit,
    CollectionLog,
    FinanceRecord,
    Project,
    Receivable,
    User,
)
from app.models.enums import (
    AlertLevel,
    AlertSource,
    AlertStatus,
    CollectionLogType,
    DebtType,
    FinanceDirection,
    FinanceStatus,
    ReceivableStatus,
)
from app.schemas.common import ApiResponse, PageResult, ok
from app.schemas.models import (
    ClientCredit,
    CollectionLogIn,
    CollectionLogOut,
    PaymentIn,
    ReceivableCreate,
    ReceivableOut,
    ReceivableScanResult,
    ReceivableSummary,
    ReceivableTier,
    ReceivableUpdate,
)

router = APIRouter(prefix="/receivables", tags=["回款清欠"])

# 逾期分级阈值（天）
TIER_OVERDUE = 0
TIER_STAGNANT = 90
TIER_BAD_DEBT = 180
# 不参与自动分级的状态
_FIXED = (ReceivableStatus.SETTLED, ReceivableStatus.WRITTEN_OFF, ReceivableStatus.LEGAL_PROCESS)

_DEBT_LABELS = {
    DebtType.PROGRESS: "进度款", DebtType.FINAL: "竣工尾款", DebtType.WARRANTY: "质保金",
    DebtType.ADVANCE: "垫资款", DebtType.OTHER: "其他欠款",
}


def _outstanding(r: Receivable) -> Decimal:
    return Decimal(str(r.amount)) - Decimal(str(r.received_amount))


def _overdue_days(r: Receivable) -> int:
    if not r.due_date or r.status in (ReceivableStatus.SETTLED, ReceivableStatus.WRITTEN_OFF):
        return 0
    if _outstanding(r) <= 0:
        return 0
    return max(0, (date.today() - r.due_date).days)


def _to_out(r: Receivable) -> ReceivableOut:
    out = ReceivableOut.model_validate(r)
    out.outstanding = _outstanding(r)
    out.overdue_days = _overdue_days(r)
    return out


def _check_project(db: Session, user: User, project_id: int | None) -> Project | None:
    if project_id is None:
        return None
    proj = db.get(Project, project_id)
    if not proj or proj.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="项目不存在")
    if not ensure_project_visible(user, project_id):
        raise HTTPException(403, detail="无权访问该项目（未授权）")
    return proj


# ---------------- 列表 ----------------
@router.get("", response_model=ApiResponse[PageResult[ReceivableOut]])
def list_receivables(
    status: ReceivableStatus | None = Query(None),
    client_id: int | None = Query(None),
    project_id: int | None = Query(None),
    debt_type: DebtType | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Receivable).where(Receivable.tenant_id == user.tenant_id)
    if status:
        stmt = stmt.where(Receivable.status == status)
    if client_id:
        stmt = stmt.where(Receivable.client_id == client_id)
    if project_id:
        stmt = stmt.where(Receivable.project_id == project_id)
    if debt_type:
        stmt = stmt.where(Receivable.debt_type == debt_type)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(Receivable.due_date.asc().nulls_last()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return ok(PageResult[ReceivableOut](
        items=[_to_out(r) for r in rows], page=page, page_size=page_size, total=total
    ))


# ---------------- 汇总与甲方信用 ----------------
@router.get("/summary", response_model=ApiResponse[ReceivableSummary])
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Receivable).where(Receivable.tenant_id == user.tenant_id)).scalars().all()
    clients = {c.id: c for c in db.execute(select(ClientUnit).where(ClientUnit.tenant_id == user.tenant_id)).scalars().all()}

    total_amount = total_received = total_out = overdue_out = Decimal("0")
    tier_counter = {"overdue": [0, Decimal("0")], "stagnant": [0, Decimal("0")], "bad_debt_risk": [0, Decimal("0")]}
    client_agg: dict = {}

    for r in rows:
        amt = Decimal(str(r.amount))
        rec = Decimal(str(r.received_amount))
        out = amt - rec
        total_amount += amt
        total_received += rec
        total_out += out
        od = _overdue_days(r)
        if od > TIER_BAD_DEBT:
            tier_counter["bad_debt_risk"][0] += 1
            tier_counter["bad_debt_risk"][1] += out
        elif od > TIER_STAGNANT:
            tier_counter["stagnant"][0] += 1
            tier_counter["stagnant"][1] += out
        elif od > TIER_OVERDUE:
            tier_counter["overdue"][0] += 1
            tier_counter["overdue"][1] += out
        if od > 0:
            overdue_out += out

        key = r.client_id
        agg = client_agg.setdefault(key, {"amount": Decimal("0"), "received": Decimal("0"), "out": Decimal("0"), "overdue_out": Decimal("0")})
        agg["amount"] += amt
        agg["received"] += rec
        agg["out"] += out
        if od > 0:
            agg["overdue_out"] += out

    tiers = [
        ReceivableTier(name="逾期", count=tier_counter["overdue"][0], outstanding=tier_counter["overdue"][1]),
        ReceivableTier(name="呆滞", count=tier_counter["stagnant"][0], outstanding=tier_counter["stagnant"][1]),
        ReceivableTier(name="坏账风险", count=tier_counter["bad_debt_risk"][0], outstanding=tier_counter["bad_debt_risk"][1]),
    ]

    client_credits = []
    for cid, agg in client_agg.items():
        ratio = float(agg["overdue_out"] / agg["amount"]) if agg["amount"] else 0.0
        score = max(0, round(100 - ratio * 100))
        level = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D"
        client_credits.append(ClientCredit(
            client_id=cid,
            client_name=clients[cid].name if cid in clients else "未指定甲方",
            total_amount=agg["amount"],
            received_amount=agg["received"],
            outstanding=agg["out"],
            overdue_outstanding=agg["overdue_out"],
            credit_score=score,
            credit_level=level,
        ))
    client_credits.sort(key=lambda c: c.outstanding, reverse=True)

    return ok(ReceivableSummary(
        total_amount=total_amount,
        total_received=total_received,
        total_outstanding=total_out,
        overdue_outstanding=overdue_out,
        tiers=tiers,
        clients=client_credits,
    ))


# ---------------- 逾期分级扫描（R-006） ----------------
@router.post("/scan", response_model=ApiResponse[ReceivableScanResult])
def scan_overdue(
    user: User = Depends(require_permission("receivable:manage")),
    db: Session = Depends(get_db),
):
    rows = db.execute(select(Receivable).where(Receivable.tenant_id == user.tenant_id)).scalars().all()
    overdue = stagnant = bad = alerts = 0
    for r in rows:
        if r.status in _FIXED or _outstanding(r) <= 0:
            continue
        od = _overdue_days(r)
        if od <= TIER_OVERDUE:
            if r.status in (ReceivableStatus.OVERDUE, ReceivableStatus.STAGNANT, ReceivableStatus.BAD_DEBT_RISK):
                r.status = ReceivableStatus.NORMAL
            continue
        if od > TIER_BAD_DEBT:
            r.status = ReceivableStatus.BAD_DEBT_RISK
            level = AlertLevel.CRITICAL
            bad += 1
        elif od > TIER_STAGNANT:
            r.status = ReceivableStatus.STAGNANT
            level = AlertLevel.HIGH
            stagnant += 1
        else:
            r.status = ReceivableStatus.OVERDUE
            level = AlertLevel.HIGH
            overdue += 1

        client_name = r.client.name if r.client else "甲方"
        title = f"债权逾期：{client_name} {_DEBT_LABELS.get(r.debt_type, '欠款')} 逾期 {od} 天，待回款 {_outstanding(r):.2f} 元"
        dup = db.execute(
            select(Alert).where(
                Alert.tenant_id == user.tenant_id,
                Alert.source == AlertSource.RECEIVABLE,
                Alert.title == title,
                Alert.status != AlertStatus.CLOSED,
            )
        ).scalars().first()
        if not dup:
            db.add(Alert(
                tenant_id=user.tenant_id,
                source=AlertSource.RECEIVABLE,
                title=title,
                project_id=r.project_id,
                level=level,
                owner_id=r.owner_id or user.id,
                due_date=r.due_date,
                status=AlertStatus.PENDING,
            ))
            alerts += 1
    db.commit()
    write_audit(db, user=user, action="scan", target_type="receivable",
                detail=f"overdue={overdue},stagnant={stagnant},bad={bad},alerts={alerts}")
    return ok(ReceivableScanResult(scanned=len(rows), overdue=overdue, stagnant=stagnant,
                                   bad_debt_risk=bad, alerts_created=alerts))


# ---------------- CRUD ----------------
@router.post("", response_model=ApiResponse[ReceivableOut])
def create_receivable(
    payload: ReceivableCreate,
    user: User = Depends(require_permission("receivable:manage")),
    db: Session = Depends(get_db),
):
    _check_project(db, user, payload.project_id)
    r = Receivable(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    write_audit(db, user=user, action="create", target_type="receivable", target_id=r.id)
    return ok(_to_out(r))


@router.get("/{rid}", response_model=ApiResponse[ReceivableOut])
def get_receivable(rid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.get(Receivable, rid)
    if not r or r.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="债权不存在")
    return ok(_to_out(r))


@router.put("/{rid}", response_model=ApiResponse[ReceivableOut])
def update_receivable(
    rid: int,
    payload: ReceivableUpdate,
    user: User = Depends(require_permission("receivable:manage")),
    db: Session = Depends(get_db),
):
    r = db.get(Receivable, rid)
    if not r or r.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="债权不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    write_audit(db, user=user, action="update", target_type="receivable", target_id=r.id)
    return ok(_to_out(r))


@router.delete("/{rid}", response_model=ApiResponse[dict])
def delete_receivable(
    rid: int,
    user: User = Depends(require_permission("receivable:manage")),
    db: Session = Depends(get_db),
):
    r = db.get(Receivable, rid)
    if not r or r.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="债权不存在")
    db.delete(r)
    db.commit()
    write_audit(db, user=user, action="delete", target_type="receivable", target_id=rid)
    return ok({"success": True})


# ---------------- 催收日志 ----------------
@router.get("/{rid}/logs", response_model=ApiResponse[list[CollectionLogOut]])
def list_logs(rid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.get(Receivable, rid)
    if not r or r.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="债权不存在")
    rows = db.execute(
        select(CollectionLog).where(CollectionLog.receivable_id == rid).order_by(CollectionLog.id.desc())
    ).scalars().all()
    return ok([CollectionLogOut.model_validate(x) for x in rows])


@router.post("/{rid}/logs", response_model=ApiResponse[CollectionLogOut])
def add_log(
    rid: int,
    payload: CollectionLogIn,
    user: User = Depends(require_permission("receivable:manage")),
    db: Session = Depends(get_db),
):
    r = db.get(Receivable, rid)
    if not r or r.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="债权不存在")
    log = CollectionLog(
        tenant_id=user.tenant_id, receivable_id=rid, type=payload.type,
        content=payload.content, result=payload.result,
        operator_id=user.id, operator_name=user.name,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    write_audit(db, user=user, action="collection_log", target_type="receivable", target_id=rid,
                detail=payload.type.value)
    return ok(CollectionLogOut.model_validate(log))


# ---------------- 回款登记（同步财税） ----------------
@router.post("/{rid}/payment", response_model=ApiResponse[ReceivableOut])
def register_payment(
    rid: int,
    payload: PaymentIn,
    user: User = Depends(require_permission("receivable:manage")),
    db: Session = Depends(get_db),
):
    r = db.get(Receivable, rid)
    if not r or r.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="债权不存在")
    amount = Decimal(str(payload.amount))
    if amount <= 0:
        raise HTTPException(400, detail="回款金额必须大于 0")

    r.received_amount = Decimal(str(r.received_amount)) + amount
    if _outstanding(r) <= 0:
        r.status = ReceivableStatus.SETTLED
    elif r.received_amount > 0:
        r.status = ReceivableStatus.PARTIAL

    # 催收日志（回款）
    db.add(CollectionLog(
        tenant_id=user.tenant_id, receivable_id=rid, type=CollectionLogType.PAYMENT,
        content=payload.remark or f"登记回款 {amount:.2f} 元", amount=amount,
        operator_id=user.id, operator_name=user.name,
    ))

    # 同步财税收入流水
    if payload.sync_finance and r.project_id:
        db.add(FinanceRecord(
            tenant_id=user.tenant_id, project_id=r.project_id, direction=FinanceDirection.INCOME,
            category="回款", amount=amount, tax_rate=Decimal("0"), tax_amount=Decimal("0"),
            has_invoice=True, counterparty=r.client.name if r.client else None,
            record_date=payload.record_date or date.today(), status=FinanceStatus.POSTED,
            remark=f"债权#{rid} 回款登记",
        ))

    db.commit()
    db.refresh(r)
    write_audit(db, user=user, action="payment", target_type="receivable", target_id=rid,
                detail=f"amount={amount}")
    return ok(_to_out(r))


# ---------------- 催收文书生成 ----------------
@router.get("/{rid}/letter", response_model=ApiResponse[dict])
def generate_letter(
    rid: int,
    kind: str = Query("reminder", description="reminder=催款函, lawyer=律师函"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    r = db.get(Receivable, rid)
    if not r or r.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="债权不存在")
    client_name = r.client.name if r.client else "贵单位"
    project_name = r.project.name if r.project else "相关工程项目"
    outstanding = _outstanding(r)
    overdue = _overdue_days(r)
    title = "律师函" if kind == "lawyer" else "催款函"
    body = (
        f"{client_name}：\n\n"
        f"  关于我司承建的「{project_name}」（合同编号：{r.contract_no or '—'}）{_DEBT_LABELS.get(r.debt_type, '欠款')}，"
        f"截至 {date.today().isoformat()}，贵单位应付未付款项为人民币 {outstanding:.2f} 元"
        f"{('，已逾期 ' + str(overdue) + ' 天') if overdue > 0 else ''}。\n\n"
        f"  我司已多次沟通催告，请贵单位于收到本函之日起 15 日内支付上述款项。"
        f"{'逾期我司将依法通过诉讼等法律途径主张权利，并要求承担违约金及相关费用。' if kind == 'lawyer' else '感谢贵单位的理解与配合。'}\n\n"
        f"                                                  示范建工集团有限公司\n"
        f"                                                  {date.today().isoformat()}"
    )
    return ok({"title": title, "content": body, "outstanding": float(outstanding), "overdue_days": overdue})
