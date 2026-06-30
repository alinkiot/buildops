"""预警中心：预警规则 + 预警事项闭环。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission, write_audit
from app.db.session import get_db
from app.models import Alert, AlertRule, User, now_utc
from app.models.enums import AlertLevel, AlertSource, AlertStatus
from app.schemas.common import ApiResponse, PageResult, ok
from app.schemas.models import (
    AlertCreate,
    AlertHandle,
    AlertOut,
    AlertRuleIn,
    AlertRuleOut,
)

router = APIRouter(prefix="/alerts", tags=["预警中心"])


# ---------------- 预警规则 ----------------
@router.get("/rules", response_model=ApiResponse[list[AlertRuleOut]])
def list_rules(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(AlertRule).where(AlertRule.tenant_id == user.tenant_id).order_by(AlertRule.id)
    ).scalars().all()
    return ok([AlertRuleOut.model_validate(r) for r in rows])


@router.post("/rules", response_model=ApiResponse[AlertRuleOut])
def create_rule(
    payload: AlertRuleIn,
    user: User = Depends(require_permission("alert:manage")),
    db: Session = Depends(get_db),
):
    exists = db.execute(
        select(AlertRule).where(AlertRule.tenant_id == user.tenant_id, AlertRule.code == payload.code)
    ).scalars().first()
    if exists:
        raise HTTPException(400, detail="规则编码已存在")
    rule = AlertRule(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    write_audit(db, user=user, action="create", target_type="alert_rule", target_id=rule.id)
    return ok(AlertRuleOut.model_validate(rule))


@router.put("/rules/{rule_id}", response_model=ApiResponse[AlertRuleOut])
def update_rule(
    rule_id: int,
    payload: AlertRuleIn,
    user: User = Depends(require_permission("alert:manage")),
    db: Session = Depends(get_db),
):
    rule = db.get(AlertRule, rule_id)
    if not rule or rule.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="规则不存在")
    for k, v in payload.model_dump(exclude={"code"}).items():
        setattr(rule, k, v)
    db.commit()
    db.refresh(rule)
    write_audit(db, user=user, action="update", target_type="alert_rule", target_id=rule.id)
    return ok(AlertRuleOut.model_validate(rule))


# ---------------- 预警事项 ----------------
@router.get("", response_model=ApiResponse[PageResult[AlertOut]])
def list_alerts(
    source: AlertSource | None = Query(None),
    level: AlertLevel | None = Query(None),
    status: AlertStatus | None = Query(None),
    project_id: int | None = Query(None),
    owner_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Alert).where(Alert.tenant_id == user.tenant_id)
    if source:
        stmt = stmt.where(Alert.source == source)
    if level:
        stmt = stmt.where(Alert.level == level)
    if status:
        stmt = stmt.where(Alert.status == status)
    if project_id:
        stmt = stmt.where(Alert.project_id == project_id)
    if owner_id:
        stmt = stmt.where(Alert.owner_id == owner_id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(Alert.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return ok(PageResult[AlertOut](
        items=[AlertOut.model_validate(r) for r in rows], page=page, page_size=page_size, total=total
    ))


@router.post("", response_model=ApiResponse[AlertOut])
def create_alert(
    payload: AlertCreate,
    user: User = Depends(require_permission("alert:manage")),
    db: Session = Depends(get_db),
):
    alert = Alert(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    write_audit(db, user=user, action="create", target_type="alert", target_id=alert.id)
    return ok(AlertOut.model_validate(alert))


@router.post("/{alert_id}/handle", response_model=ApiResponse[AlertOut])
def handle_alert(
    alert_id: int,
    payload: AlertHandle,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alert = db.get(Alert, alert_id)
    if not alert or alert.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="预警不存在")
    alert.status = payload.status
    alert.handle_remark = payload.handle_remark
    if payload.status == AlertStatus.CLOSED:
        alert.closed_at = now_utc()
    db.commit()
    db.refresh(alert)
    write_audit(
        db, user=user, action="handle", target_type="alert", target_id=alert.id,
        detail=f"status={payload.status.value}",
    )
    return ok(AlertOut.model_validate(alert))
