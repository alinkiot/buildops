"""认证：登录、当前用户。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import collect_permissions, get_current_user, write_audit
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models import User, now_utc
from app.models.enums import CommonStatus
from app.schemas.common import ApiResponse, ok
from app.schemas.models import CurrentUser, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=ApiResponse[TokenResponse])
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.username == payload.username)).scalars().first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if user.status != CommonStatus.ENABLED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用")

    user.last_login_at = now_utc()
    db.commit()
    token = create_access_token(user.id, extra={"tenant_id": user.tenant_id})
    write_audit(db, user=user, action="login", ip=request.client.host if request.client else None)
    return ok(TokenResponse(access_token=token))


@router.get("/me", response_model=ApiResponse[CurrentUser])
def me(user: User = Depends(get_current_user)):
    data = CurrentUser.model_validate(user)
    data.permissions = sorted(collect_permissions(user))
    return ok(data)
