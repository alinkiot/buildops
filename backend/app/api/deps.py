"""API 依赖：当前用户、权限校验、审计日志。"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import AuditLog, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效或过期的登录凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exc
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except Exception:
        raise credentials_exc

    user = db.get(User, user_id)
    if user is None or user.status.value != "enabled":
        raise credentials_exc
    # 挂到 request.state 便于审计
    request.state.current_user = user
    return user


def collect_permissions(user: User) -> set[str]:
    if user.is_superadmin:
        return {"*"}
    codes: set[str] = set()
    for role in user.roles:
        for perm in role.permissions:
            codes.add(perm.code)
    return codes


def can_see_all_projects(user: User) -> bool:
    """是否拥有全部项目数据范围（超管或任一角色数据范围为 all）。"""
    if user.is_superadmin:
        return True
    return any(getattr(r.data_scope, "value", r.data_scope) == "all" for r in user.roles)


def authorized_project_ids(user: User) -> set[int] | None:
    """返回用户可见的项目 id 集合；None 表示不受项目范围限制（可见全部）。"""
    if can_see_all_projects(user):
        return None
    return {p.id for p in user.projects}


def ensure_project_visible(user: User, project_id: int | None) -> bool:
    """校验用户是否有权访问指定项目（用于项目级数据范围强制）。"""
    if project_id is None:
        return True
    ids = authorized_project_ids(user)
    return ids is None or project_id in ids


def require_permission(code: str):
    """权限校验依赖工厂。"""

    def checker(user: User = Depends(get_current_user)) -> User:
        perms = collect_permissions(user)
        if "*" in perms or code in perms:
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"缺少权限：{code}")

    return checker


def write_audit(
    db: Session,
    *,
    user: User | None,
    action: str,
    target_type: str | None = None,
    target_id: str | int | None = None,
    detail: str | None = None,
    ip: str | None = None,
) -> None:
    log = AuditLog(
        tenant_id=user.tenant_id if user else 0,
        user_id=user.id if user else None,
        username=user.username if user else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        detail=detail,
        ip=ip,
    )
    db.add(log)
    db.commit()
