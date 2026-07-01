"""用户反馈/建议。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, write_audit
from app.db.session import get_db
from app.models import Feedback, User
from app.models.enums import FeedbackStatus
from app.schemas.common import ApiResponse, PageResult, ok
from app.schemas.models import FeedbackCreate, FeedbackOut, FeedbackStatusUpdate

router = APIRouter(prefix="/feedback", tags=["用户反馈"])


@router.post("", response_model=ApiResponse[FeedbackOut])
def create_feedback(
    payload: FeedbackCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交反馈/建议（任何登录用户均可）。"""
    fb = Feedback(
        tenant_id=user.tenant_id,
        user_id=user.id,
        title=payload.title,
        description=payload.description,
        page_url=payload.page_url,
        status=FeedbackStatus.PENDING,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    write_audit(db, user=user, action="create", target_type="feedback", target_id=fb.id)
    return ok(FeedbackOut.model_validate(fb))


@router.get("", response_model=ApiResponse[PageResult[FeedbackOut]])
def list_feedback(
    status: FeedbackStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取反馈列表（分页）。"""
    stmt = select(Feedback).where(Feedback.tenant_id == user.tenant_id)
    if status:
        stmt = stmt.where(Feedback.status == status)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(Feedback.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return ok(PageResult[FeedbackOut](
        items=[FeedbackOut.model_validate(r) for r in rows], page=page, page_size=page_size, total=total
    ))


@router.put("/{feedback_id}/status", response_model=ApiResponse[FeedbackOut])
def update_feedback_status(
    feedback_id: int,
    payload: FeedbackStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新反馈状态。"""
    fb = db.get(Feedback, feedback_id)
    if not fb or fb.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="反馈不存在")
    fb.status = payload.status
    db.commit()
    db.refresh(fb)
    write_audit(
        db, user=user, action="update", target_type="feedback", target_id=fb.id,
        detail=f"status={payload.status.value}",
    )
    return ok(FeedbackOut.model_validate(fb))
