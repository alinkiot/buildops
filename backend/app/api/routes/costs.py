"""成本管理：预算科目、支出登记(超预算检测+审批+预警R-003)、偏差汇总、成本回写。"""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ensure_project_visible, get_current_user, require_permission, write_audit
from app.db.session import get_db
from app.models import Alert, Budget, Expense, Project, User
from app.models.enums import AlertLevel, AlertSource, AlertStatus, ExpenseStatus, ExpenseType
from app.schemas.common import ApiResponse, PageResult, ok
from app.schemas.models import (
    BudgetDeviation,
    BudgetIn,
    BudgetOut,
    BudgetUpdate,
    CostSummary,
    ExpenseApprove,
    ExpenseCreate,
    ExpenseOut,
)

router = APIRouter(prefix="/costs", tags=["成本管理"])

# 计入已发生成本的支出状态（驳回不计）
_COUNTED = (ExpenseStatus.REGISTERED, ExpenseStatus.PENDING_APPROVAL, ExpenseStatus.PAID)


def _check_project(db: Session, user: User, project_id: int) -> Project:
    proj = db.get(Project, project_id)
    if not proj or proj.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="项目不存在")
    if not ensure_project_visible(user, project_id):
        raise HTTPException(403, detail="无权访问该项目（未授权）")
    return proj


def _category_actual(db: Session, project_id: int, category: str | None, exclude_id: int | None = None) -> Decimal:
    if not category:
        return Decimal("0")
    stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.project_id == project_id,
        Expense.category == category,
        Expense.status.in_(_COUNTED),
    )
    if exclude_id:
        stmt = stmt.where(Expense.id != exclude_id)
    return Decimal(str(db.execute(stmt).scalar_one()))


def _sync_project_cost(db: Session, project: Project) -> None:
    """把项目已发生成本回写到 Project.cost_amount（驾驶舱口径）。"""
    total = db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.project_id == project.id, Expense.status.in_(_COUNTED)
        )
    ).scalar_one()
    project.cost_amount = Decimal(str(total))


# ---------------- 预算 ----------------
@router.get("/budgets", response_model=ApiResponse[list[BudgetOut]])
def list_budgets(
    project_id: int = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_project(db, user, project_id)
    rows = db.execute(
        select(Budget).where(Budget.tenant_id == user.tenant_id, Budget.project_id == project_id).order_by(Budget.id)
    ).scalars().all()
    return ok([BudgetOut.model_validate(r) for r in rows])


@router.post("/budgets", response_model=ApiResponse[BudgetOut])
def create_budget(
    payload: BudgetIn,
    user: User = Depends(require_permission("cost:manage")),
    db: Session = Depends(get_db),
):
    _check_project(db, user, payload.project_id)
    exists = db.execute(
        select(Budget).where(Budget.project_id == payload.project_id, Budget.category == payload.category)
    ).scalars().first()
    if exists:
        raise HTTPException(400, detail="该项目下成本科目已存在")
    b = Budget(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(b)
    db.commit()
    db.refresh(b)
    write_audit(db, user=user, action="create", target_type="budget", target_id=b.id)
    return ok(BudgetOut.model_validate(b))


@router.put("/budgets/{bid}", response_model=ApiResponse[BudgetOut])
def update_budget(
    bid: int,
    payload: BudgetUpdate,
    user: User = Depends(require_permission("cost:manage")),
    db: Session = Depends(get_db),
):
    b = db.get(Budget, bid)
    if not b or b.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="预算科目不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(b, k, v)
    db.commit()
    db.refresh(b)
    return ok(BudgetOut.model_validate(b))


@router.delete("/budgets/{bid}", response_model=ApiResponse[dict])
def delete_budget(
    bid: int,
    user: User = Depends(require_permission("cost:manage")),
    db: Session = Depends(get_db),
):
    b = db.get(Budget, bid)
    if not b or b.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="预算科目不存在")
    db.delete(b)
    db.commit()
    return ok({"success": True})


# ---------------- 支出 ----------------
@router.get("/expenses", response_model=ApiResponse[PageResult[ExpenseOut]])
def list_expenses(
    project_id: int = Query(...),
    type: ExpenseType | None = Query(None),
    status: ExpenseStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_project(db, user, project_id)
    stmt = select(Expense).where(Expense.tenant_id == user.tenant_id, Expense.project_id == project_id)
    if type:
        stmt = stmt.where(Expense.type == type)
    if status:
        stmt = stmt.where(Expense.status == status)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(Expense.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return ok(PageResult[ExpenseOut](
        items=[ExpenseOut.model_validate(r) for r in rows], page=page, page_size=page_size, total=total
    ))


@router.post("/expenses", response_model=ApiResponse[ExpenseOut])
def create_expense(
    payload: ExpenseCreate,
    user: User = Depends(require_permission("cost:manage")),
    db: Session = Depends(get_db),
):
    """登记支出：若导致科目累计超预算，则进入待审批并生成预警（R-003）。"""
    proj = _check_project(db, user, payload.project_id)
    amount = Decimal(str(payload.amount))

    over = False
    budget = None
    if payload.category:
        budget = db.execute(
            select(Budget).where(Budget.project_id == payload.project_id, Budget.category == payload.category)
        ).scalars().first()
        if budget:
            cumulative = _category_actual(db, payload.project_id, payload.category) + amount
            if cumulative > Decimal(str(budget.budget_amount)):
                over = True

    exp = Expense(
        tenant_id=user.tenant_id,
        project_id=payload.project_id,
        category=payload.category,
        type=payload.type,
        amount=amount,
        payee=payload.payee,
        expense_date=payload.expense_date,
        has_invoice=payload.has_invoice,
        remark=payload.remark,
        applicant_id=user.id,
        over_budget=over,
        status=ExpenseStatus.PENDING_APPROVAL if over else ExpenseStatus.REGISTERED,
    )
    db.add(exp)
    db.flush()

    if over and budget:
        over_amt = (_category_actual(db, payload.project_id, payload.category, exclude_id=exp.id) + amount) - Decimal(str(budget.budget_amount))
        db.add(Alert(
            tenant_id=user.tenant_id,
            source=AlertSource.COST,
            title=f"支出超预算：『{payload.category}』超出 {over_amt:.2f} 元，待审批",
            project_id=payload.project_id,
            level=AlertLevel.HIGH,
            owner_id=proj.owner_id or user.id,
            status=AlertStatus.PENDING,
        ))

    _sync_project_cost(db, proj)
    db.commit()
    db.refresh(exp)
    write_audit(db, user=user, action="create", target_type="expense", target_id=exp.id,
                detail=f"over_budget={over}")
    return ok(ExpenseOut.model_validate(exp))


@router.post("/expenses/{eid}/approve", response_model=ApiResponse[ExpenseOut])
def approve_expense(
    eid: int,
    payload: ExpenseApprove,
    user: User = Depends(require_permission("cost:approve")),
    db: Session = Depends(get_db),
):
    exp = db.get(Expense, eid)
    if not exp or exp.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="支出不存在")
    if exp.status != ExpenseStatus.PENDING_APPROVAL:
        raise HTTPException(400, detail="该支出无需审批")
    exp.status = ExpenseStatus.PAID if payload.approved else ExpenseStatus.REJECTED
    exp.approver_id = user.id
    exp.approve_remark = payload.approve_remark
    proj = db.get(Project, exp.project_id)
    _sync_project_cost(db, proj)
    db.commit()
    db.refresh(exp)
    write_audit(db, user=user, action="approve", target_type="expense", target_id=exp.id,
                detail="approved" if payload.approved else "rejected")
    return ok(ExpenseOut.model_validate(exp))


# ---------------- 成本偏差汇总 ----------------
@router.get("/summary", response_model=ApiResponse[CostSummary])
def cost_summary(
    project_id: int = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_project(db, user, project_id)
    budgets = db.execute(
        select(Budget).where(Budget.project_id == project_id).order_by(Budget.id)
    ).scalars().all()

    deviations: list[BudgetDeviation] = []
    total_budget = Decimal("0")
    total_actual = Decimal("0")
    for b in budgets:
        ba = Decimal(str(b.budget_amount))
        actual = _category_actual(db, project_id, b.category)
        total_budget += ba
        total_actual += actual
        rate = float((actual - ba) / ba * 100) if ba else 0.0
        deviations.append(BudgetDeviation(
            category=b.category,
            budget_amount=ba,
            actual_amount=actual,
            remaining=ba - actual,
            deviation_rate=round(rate, 1),
            over_budget=actual > ba,
        ))

    # 无预算科目但有支出的部分也纳入总实际
    other_actual = db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.project_id == project_id,
            Expense.status.in_(_COUNTED),
            Expense.category.is_(None),
        )
    ).scalar_one()
    total_actual += Decimal(str(other_actual))

    pending = db.execute(
        select(func.count()).select_from(Expense).where(
            Expense.project_id == project_id, Expense.status == ExpenseStatus.PENDING_APPROVAL
        )
    ).scalar_one()
    no_invoice = db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.project_id == project_id,
            Expense.status.in_(_COUNTED),
            Expense.has_invoice.is_(False),
        )
    ).scalar_one()

    rate = float((total_actual - total_budget) / total_budget * 100) if total_budget else 0.0
    return ok(CostSummary(
        project_id=project_id,
        total_budget=total_budget,
        total_actual=total_actual,
        total_remaining=total_budget - total_actual,
        deviation_rate=round(rate, 1),
        pending_approval=pending,
        no_invoice_amount=Decimal(str(no_invoice)),
        deviations=deviations,
    ))
