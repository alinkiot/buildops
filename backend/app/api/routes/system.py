"""系统设置：部门、用户、角色、权限、审计日志。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission, write_audit
from app.core.security import hash_password
from app.db.session import get_db
from app.models import (
    AuditLog,
    Department,
    Permission,
    Project,
    Role,
    User,
)
from app.models.enums import CommonStatus
from app.schemas.common import ApiResponse, PageResult, ok
from app.schemas.models import (
    DepartmentIn,
    DepartmentOut,
    PermissionOut,
    ProjectBrief,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    UserCreate,
    UserOut,
    UserProjectAuth,
    UserUpdate,
)

router = APIRouter(prefix="/system", tags=["系统设置"])


# ---------------- 部门 ----------------
@router.get("/departments", response_model=ApiResponse[list[DepartmentOut]])
def list_departments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Department).where(Department.tenant_id == user.tenant_id).order_by(Department.sort)
    ).scalars().all()
    return ok([DepartmentOut.model_validate(r) for r in rows])


@router.post("/departments", response_model=ApiResponse[DepartmentOut])
def create_department(
    payload: DepartmentIn,
    request: Request,
    user: User = Depends(require_permission("system:dept:manage")),
    db: Session = Depends(get_db),
):
    dept = Department(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    write_audit(db, user=user, action="create", target_type="department", target_id=dept.id)
    return ok(DepartmentOut.model_validate(dept))


# ---------------- 权限 ----------------
@router.get("/permissions", response_model=ApiResponse[list[PermissionOut]])
def list_permissions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Permission).order_by(Permission.sort)).scalars().all()
    return ok([PermissionOut.model_validate(r) for r in rows])


# ---------------- 角色 ----------------
@router.get("/roles", response_model=ApiResponse[list[RoleOut]])
def list_roles(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Role).where(Role.tenant_id == user.tenant_id).order_by(Role.id)
    ).scalars().all()
    return ok([RoleOut.model_validate(r) for r in rows])


def _load_permissions(db: Session, codes: list[str]) -> list[Permission]:
    if not codes:
        return []
    return db.execute(select(Permission).where(Permission.code.in_(codes))).scalars().all()


@router.post("/roles", response_model=ApiResponse[RoleOut])
def create_role(
    payload: RoleCreate,
    user: User = Depends(require_permission("system:role:manage")),
    db: Session = Depends(get_db),
):
    exists = db.execute(
        select(Role).where(Role.tenant_id == user.tenant_id, Role.code == payload.code)
    ).scalars().first()
    if exists:
        raise HTTPException(400, detail="角色编码已存在")
    role = Role(
        tenant_id=user.tenant_id,
        code=payload.code,
        name=payload.name,
        data_scope=payload.data_scope,
        remark=payload.remark,
    )
    role.permissions = _load_permissions(db, payload.permission_codes)
    db.add(role)
    db.commit()
    db.refresh(role)
    write_audit(db, user=user, action="create", target_type="role", target_id=role.id)
    return ok(RoleOut.model_validate(role))


@router.put("/roles/{role_id}", response_model=ApiResponse[RoleOut])
def update_role(
    role_id: int,
    payload: RoleUpdate,
    user: User = Depends(require_permission("system:role:manage")),
    db: Session = Depends(get_db),
):
    role = db.get(Role, role_id)
    if not role or role.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="角色不存在")
    data = payload.model_dump(exclude_unset=True)
    if "permission_codes" in data:
        role.permissions = _load_permissions(db, data.pop("permission_codes") or [])
    for k, v in data.items():
        setattr(role, k, v)
    db.commit()
    db.refresh(role)
    write_audit(db, user=user, action="update", target_type="role", target_id=role.id)
    return ok(RoleOut.model_validate(role))


# ---------------- 用户 ----------------
@router.get("/users", response_model=ApiResponse[PageResult[UserOut]])
def list_users(
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(User).where(User.tenant_id == user.tenant_id)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where((User.username.like(like)) | (User.name.like(like)))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return ok(PageResult[UserOut](
        items=[UserOut.model_validate(r) for r in rows], page=page, page_size=page_size, total=total
    ))


@router.post("/users", response_model=ApiResponse[UserOut])
def create_user(
    payload: UserCreate,
    user: User = Depends(require_permission("system:user:manage")),
    db: Session = Depends(get_db),
):
    exists = db.execute(
        select(User).where(User.tenant_id == user.tenant_id, User.username == payload.username)
    ).scalars().first()
    if exists:
        raise HTTPException(400, detail="用户名已存在")
    new_user = User(
        tenant_id=user.tenant_id,
        username=payload.username,
        password_hash=hash_password(payload.password),
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        department_id=payload.department_id,
    )
    if payload.role_ids:
        new_user.roles = db.execute(
            select(Role).where(Role.tenant_id == user.tenant_id, Role.id.in_(payload.role_ids))
        ).scalars().all()
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    write_audit(db, user=user, action="create", target_type="user", target_id=new_user.id)
    return ok(UserOut.model_validate(new_user))


@router.put("/users/{user_id}", response_model=ApiResponse[UserOut])
def update_user(
    user_id: int,
    payload: UserUpdate,
    user: User = Depends(require_permission("system:user:manage")),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if not target or target.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="用户不存在")
    data = payload.model_dump(exclude_unset=True)
    if "role_ids" in data:
        ids = data.pop("role_ids") or []
        target.roles = db.execute(
            select(Role).where(Role.tenant_id == user.tenant_id, Role.id.in_(ids))
        ).scalars().all()
    for k, v in data.items():
        setattr(target, k, v)
    db.commit()
    db.refresh(target)
    write_audit(db, user=user, action="update", target_type="user", target_id=target.id)
    return ok(UserOut.model_validate(target))


@router.post("/users/{user_id}/reset-password", response_model=ApiResponse[dict])
def reset_password(
    user_id: int,
    new_password: str = Query(min_length=6),
    user: User = Depends(require_permission("system:user:manage")),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if not target or target.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="用户不存在")
    target.password_hash = hash_password(new_password)
    db.commit()
    write_audit(db, user=user, action="reset_password", target_type="user", target_id=target.id)
    return ok({"success": True})


# ---------------- 用户项目授权（数据范围） ----------------
@router.get("/users/{user_id}/projects", response_model=ApiResponse[list[ProjectBrief]])
def get_user_projects(
    user_id: int,
    user: User = Depends(require_permission("system:user:manage")),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if not target or target.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="用户不存在")
    return ok([ProjectBrief.model_validate(p) for p in target.projects])


@router.put("/users/{user_id}/projects", response_model=ApiResponse[list[ProjectBrief]])
def set_user_projects(
    user_id: int,
    payload: UserProjectAuth,
    user: User = Depends(require_permission("system:user:manage")),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if not target or target.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="用户不存在")
    projects = db.execute(
        select(Project).where(Project.tenant_id == user.tenant_id, Project.id.in_(payload.project_ids or [-1]))
    ).scalars().all()
    target.projects = projects
    db.commit()
    db.refresh(target)
    write_audit(db, user=user, action="set_projects", target_type="user", target_id=target.id,
                detail=f"projects={[p.id for p in projects]}")
    return ok([ProjectBrief.model_validate(p) for p in target.projects])



@router.get("/audit-logs", response_model=ApiResponse[PageResult[dict]])
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    action: str | None = Query(None),
    user: User = Depends(require_permission("system:audit:view")),
    db: Session = Depends(get_db),
):
    stmt = select(AuditLog).where(AuditLog.tenant_id == user.tenant_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    items = [
        {
            "id": r.id,
            "username": r.username,
            "action": r.action,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "detail": r.detail,
            "ip": r.ip,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return ok(PageResult[dict](items=items, page=page, page_size=page_size, total=total))
