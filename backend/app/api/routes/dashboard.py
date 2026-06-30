"""驾驶舱：经营总览聚合指标。"""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import authorized_project_ids, get_current_user
from app.db.session import get_db
from app.models import (
    Alert,
    Budget,
    ClientUnit,
    DocItem,
    Expense,
    FinanceRecord,
    Project,
    Qualification,
    Receivable,
    Tender,
    User,
    Worker,
    PayrollRecord,
)
from app.models.enums import (
    AlertStatus,
    DocStatus,
    ExpenseStatus,
    FinanceDirection,
    FinanceStatus,
    ProjectStatus,
    QualificationStatus,
    ReceivableStatus,
    TenderStatus,
    WorkerStatus,
)
from app.schemas.common import ApiResponse, ok
from app.schemas.models import (
    BidHealth,
    CostHealth,
    DashboardData,
    DashboardOverview,
    DocHealth,
    FinanceHealth,
    LaborHealth,
    ModuleOverview,
    NameValue,
    QualHealth,
    ReceivableHealth,
)
from datetime import date

router = APIRouter(prefix="/dashboard", tags=["驾驶舱"])

_PROJECT_STATUS_LABELS = {
    ProjectStatus.PREPARING: "筹备",
    ProjectStatus.ONGOING: "在建",
    ProjectStatus.SUSPENDED: "停工",
    ProjectStatus.COMPLETED: "竣工",
    ProjectStatus.SETTLING: "结算中",
    ProjectStatus.COLLECTING: "清欠中",
    ProjectStatus.ARCHIVED: "归档",
}

_SOURCE_LABELS = {
    "qualification": "资质",
    "document": "资料",
    "cost": "成本",
    "finance": "财税",
    "receivable": "回款",
    "secret": "涉密",
    "bid": "招投标",
    "labor": "劳务",
}

_LEVEL_LABELS = {"low": "一般", "medium": "关注", "high": "预警", "critical": "高风险"}

_COST_COUNTED = (ExpenseStatus.REGISTERED, ExpenseStatus.PENDING_APPROVAL, ExpenseStatus.PAID)
_FIN_COUNTED = (FinanceStatus.PENDING, FinanceStatus.POSTED, FinanceStatus.PENDING_INVOICE, FinanceStatus.ABNORMAL)


def _module_overview(db: Session, tid: int, auth_ids: set[int] | None = None) -> ModuleOverview:
    today = date.today()

    def _scope(stmt, col):
        """数据范围：受限用户仅统计授权项目的项目级数据。"""
        if auth_ids is not None:
            return stmt.where(col.in_(auth_ids or {-1}))
        return stmt

    # 资质健康度（按有效期实时计算，不依赖是否扫描）
    quals = db.execute(select(Qualification).where(Qualification.tenant_id == tid)).scalars().all()
    q_total = len(quals)
    q_expired = q_expiring = 0
    for q in quals:
        if q.status == QualificationStatus.DISABLED or not q.valid_to:
            continue
        days = (q.valid_to - today).days
        if days < 0:
            q_expired += 1
        elif days <= 90:
            q_expiring += 1
    q_valid = q_total - q_expired - q_expiring
    q_score = round((q_valid + q_expiring * 0.5) / q_total * 100) if q_total else 100

    # 资料完整度（全租户必需项口径）
    items = db.execute(_scope(select(DocItem).where(DocItem.tenant_id == tid), DocItem.project_id)).scalars().all()
    req_total = sum(1 for i in items if i.required)
    approved = sum(1 for i in items if i.required and i.status in (DocStatus.APPROVED, DocStatus.ARCHIVED))
    missing = sum(1 for i in items if i.status == DocStatus.MISSING)
    completeness = round(approved / req_total * 100, 1) if req_total else 0.0

    # 成本偏差
    budgets = db.execute(_scope(select(Budget).where(Budget.tenant_id == tid), Budget.project_id)).scalars().all()
    total_budget = sum((Decimal(str(b.budget_amount)) for b in budgets), Decimal("0"))
    expenses = db.execute(
        _scope(select(Expense).where(Expense.tenant_id == tid, Expense.status.in_(_COST_COUNTED)), Expense.project_id)
    ).scalars().all()
    total_actual = sum((Decimal(str(e.amount)) for e in expenses), Decimal("0"))
    # 按项目+科目判断超预算项目数
    budget_map = {(b.project_id, b.category): Decimal(str(b.budget_amount)) for b in budgets}
    actual_map: dict = {}
    for e in expenses:
        if e.category:
            actual_map[(e.project_id, e.category)] = actual_map.get((e.project_id, e.category), Decimal("0")) + Decimal(str(e.amount))
    over_projects = {pid for (pid, cat), act in actual_map.items() if (pid, cat) in budget_map and act > budget_map[(pid, cat)]}
    pending_appr = sum(1 for e in expenses if e.status == ExpenseStatus.PENDING_APPROVAL)
    dev_rate = float((total_actual - total_budget) / total_budget * 100) if total_budget else 0.0

    # 财税利润
    fins = db.execute(
        _scope(select(FinanceRecord).where(FinanceRecord.tenant_id == tid, FinanceRecord.status.in_(_FIN_COUNTED)), FinanceRecord.project_id)
    ).scalars().all()
    f_income = sum((Decimal(str(r.amount)) for r in fins if r.direction == FinanceDirection.INCOME), Decimal("0"))
    f_expense = sum((Decimal(str(r.amount)) for r in fins if r.direction == FinanceDirection.EXPENSE), Decimal("0"))
    f_tax = sum((Decimal(str(r.tax_amount)) for r in fins), Decimal("0"))
    f_no_invoice = sum((Decimal(str(r.amount)) for r in fins if r.direction == FinanceDirection.EXPENSE and not r.has_invoice), Decimal("0"))
    no_invoice_ratio = float(f_no_invoice / f_expense * 100) if f_expense else 0.0

    # 回款分级与甲方信用
    recs = db.execute(_scope(select(Receivable).where(Receivable.tenant_id == tid), Receivable.project_id)).scalars().all()
    clients = {c.id: c.name for c in db.execute(select(ClientUnit).where(ClientUnit.tenant_id == tid)).scalars().all()}
    total_out = overdue_out = Decimal("0")
    r_overdue = r_stagnant = r_bad = 0
    client_overdue: dict = {}
    client_total: dict = {}
    for r in recs:
        out = Decimal(str(r.amount)) - Decimal(str(r.received_amount))
        total_out += out
        client_total[r.client_id] = client_total.get(r.client_id, Decimal("0")) + Decimal(str(r.amount))
        od = 0
        if r.due_date and r.status not in (ReceivableStatus.SETTLED, ReceivableStatus.WRITTEN_OFF) and out > 0:
            od = max(0, (today - r.due_date).days)
        if od > 180:
            r_bad += 1
        elif od > 90:
            r_stagnant += 1
        elif od > 0:
            r_overdue += 1
        if od > 0:
            overdue_out += out
            client_overdue[r.client_id] = client_overdue.get(r.client_id, Decimal("0")) + out
    # 最差甲方（逾期占比最高）
    worst = None
    worst_ratio = -1.0
    for cid, ov in client_overdue.items():
        tot = client_total.get(cid, Decimal("0"))
        ratio = float(ov / tot) if tot else 0.0
        if ratio > worst_ratio:
            worst_ratio = ratio
            worst = cid
    worst_name = clients.get(worst, "未指定甲方") if worst is not None else None
    worst_level = None
    if worst is not None:
        score = max(0, round(100 - worst_ratio * 100))
        worst_level = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D"

    # 招投标
    tenders = db.execute(select(Tender).where(Tender.tenant_id == tid)).scalars().all()
    t_counter: dict = {}
    for t in tenders:
        t_counter[t.status] = t_counter.get(t.status, 0) + 1
    t_won = t_counter.get(TenderStatus.WON, 0)
    t_lost = t_counter.get(TenderStatus.LOST, 0)
    t_submitted = t_counter.get(TenderStatus.BIDDED, 0)
    t_bidded = t_won + t_lost + t_submitted
    t_decided = t_won + t_lost
    t_win_rate = round(t_won / t_decided * 100, 1) if t_decided else 0.0
    t_dep_out = sum((Decimal(str(t.deposit_amount)) for t in tenders if not t.deposit_returned and t.deposit_amount), Decimal("0"))
    t_dep_overdue = sum(1 for t in tenders if not t.deposit_returned and t.deposit_amount and t.deposit_due and t.deposit_due < today)

    # 劳务
    workers = db.execute(_scope(select(Worker).where(Worker.tenant_id == tid), Worker.project_id)).scalars().all()
    onsite = [w for w in workers if w.status == WorkerStatus.ONSITE]
    w_contract_missing = sum(1 for w in onsite if not w.contract_signed)
    w_insurance_missing = sum(1 for w in onsite if w.insurance_expiry is None or w.insurance_expiry < today)
    w_risk = sum(1 for w in workers if w.risk_tag)
    w_unpaid = db.execute(
        select(func.coalesce(func.sum(PayrollRecord.amount), 0)).where(
            PayrollRecord.tenant_id == tid, PayrollRecord.paid.is_(False)
        )
    ).scalar_one()

    return ModuleOverview(
        qualification=QualHealth(total=q_total, valid=q_valid, expiring=q_expiring, expired=q_expired, health_score=q_score),
        document=DocHealth(required_total=req_total, approved=approved, missing=missing, completeness=completeness),
        cost=CostHealth(total_budget=total_budget, total_actual=total_actual, deviation_rate=round(dev_rate, 1),
                        over_budget_projects=len(over_projects), pending_approval=pending_appr),
        finance=FinanceHealth(total_income=f_income, total_expense=f_expense, total_tax=f_tax,
                              net_profit=f_income - f_expense - f_tax, no_invoice_ratio=round(no_invoice_ratio, 1)),
        receivable=ReceivableHealth(total_outstanding=total_out, overdue_outstanding=overdue_out,
                                    overdue=r_overdue, stagnant=r_stagnant, bad_debt_risk=r_bad,
                                    worst_client=worst_name, worst_client_level=worst_level),
        bid=BidHealth(total=len(tenders), bidded=t_bidded, won=t_won, win_rate=t_win_rate,
                      deposit_outstanding=t_dep_out, deposit_overdue=t_dep_overdue),
        labor=LaborHealth(total=len(workers), onsite=len(onsite), contract_missing=w_contract_missing,
                          insurance_missing=w_insurance_missing, risk_workers=w_risk,
                          unpaid_amount=Decimal(str(w_unpaid))),
    )


@router.get("", response_model=ApiResponse[DashboardData])
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = user.tenant_id
    auth_ids = authorized_project_ids(user)
    pstmt = select(Project).where(Project.tenant_id == tid)
    if auth_ids is not None:
        pstmt = pstmt.where(Project.id.in_(auth_ids or {-1}))
    projects = db.execute(pstmt).scalars().all()

    project_count = len(projects)
    ongoing_count = sum(1 for p in projects if p.status == ProjectStatus.ONGOING)
    contract = sum((Decimal(p.contract_amount) for p in projects), Decimal("0"))
    received = sum((Decimal(p.received_amount) for p in projects), Decimal("0"))
    cost = sum((Decimal(p.cost_amount) for p in projects), Decimal("0"))
    profit = received - cost
    receivable = contract - received

    alert_count = db.execute(
        select(func.count()).select_from(Alert).where(Alert.tenant_id == tid)
    ).scalar_one()
    pending_count = db.execute(
        select(func.count()).select_from(Alert).where(
            Alert.tenant_id == tid,
            Alert.status.in_([AlertStatus.PENDING, AlertStatus.PROCESSING, AlertStatus.OVERDUE]),
        )
    ).scalar_one()

    overview = DashboardOverview(
        project_count=project_count,
        ongoing_count=ongoing_count,
        contract_amount=contract,
        received_amount=received,
        cost_amount=cost,
        profit_amount=profit,
        receivable_amount=receivable,
        alert_count=alert_count,
        pending_alert_count=pending_count,
    )

    # 项目利润排行（按 收入-成本 倒序取前 10）
    ranked = sorted(
        projects, key=lambda p: Decimal(p.received_amount) - Decimal(p.cost_amount), reverse=True
    )[:10]
    profit_rank = [
        {
            "id": p.id,
            "name": p.name,
            "contract_amount": float(p.contract_amount),
            "received_amount": float(p.received_amount),
            "cost_amount": float(p.cost_amount),
            "profit": float(Decimal(p.received_amount) - Decimal(p.cost_amount)),
            "receivable": float(Decimal(p.contract_amount) - Decimal(p.received_amount)),
        }
        for p in ranked
    ]

    # 预警按来源
    by_source_rows = db.execute(
        select(Alert.source, func.count()).where(Alert.tenant_id == tid).group_by(Alert.source)
    ).all()
    alert_by_source = [
        NameValue(name=_SOURCE_LABELS.get(s.value if hasattr(s, "value") else s, str(s)), value=c)
        for s, c in by_source_rows
    ]

    by_level_rows = db.execute(
        select(Alert.level, func.count()).where(Alert.tenant_id == tid).group_by(Alert.level)
    ).all()
    alert_by_level = [
        NameValue(name=_LEVEL_LABELS.get(l.value if hasattr(l, "value") else l, str(l)), value=c)
        for l, c in by_level_rows
    ]

    # 项目按状态
    status_counter: dict = {}
    for p in projects:
        status_counter[p.status] = status_counter.get(p.status, 0) + 1
    project_by_status = [
        NameValue(name=_PROJECT_STATUS_LABELS.get(st, str(st)), value=cnt)
        for st, cnt in status_counter.items()
    ]

    return ok(DashboardData(
        overview=overview,
        project_profit_rank=profit_rank,
        alert_by_source=alert_by_source,
        alert_by_level=alert_by_level,
        project_by_status=project_by_status,
        modules=_module_overview(db, tid, auth_ids),
    ))
