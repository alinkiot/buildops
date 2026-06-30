"""项目中心：甲方单位 + 项目。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import authorized_project_ids, get_current_user, require_permission, write_audit
from app.db.session import get_db
from app.models import ClientUnit, Project, User
from app.models.enums import ProjectStatus
from app.schemas.common import ApiResponse, PageResult, ok
from app.schemas.models import (
    ClientIn,
    ClientOut,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["项目中心"])


# ---------------- 甲方 ----------------
@router.get("/clients", response_model=ApiResponse[list[ClientOut]])
def list_clients(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(ClientUnit).where(ClientUnit.tenant_id == user.tenant_id).order_by(ClientUnit.id)
    ).scalars().all()
    return ok([ClientOut.model_validate(r) for r in rows])


@router.post("/clients", response_model=ApiResponse[ClientOut])
def create_client(
    payload: ClientIn,
    user: User = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db),
):
    client = ClientUnit(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    write_audit(db, user=user, action="create", target_type="client", target_id=client.id)
    return ok(ClientOut.model_validate(client))


# ---------------- 项目 ----------------
@router.get("", response_model=ApiResponse[PageResult[ProjectOut]])
def list_projects(
    keyword: str | None = Query(None),
    status: ProjectStatus | None = Query(None),
    client_id: int | None = Query(None),
    owner_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Project).where(Project.tenant_id == user.tenant_id)
    # 数据范围：项目授权
    auth_ids = authorized_project_ids(user)
    if auth_ids is not None:
        stmt = stmt.where(Project.id.in_(auth_ids or {-1}))
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where((Project.name.like(like)) | (Project.code.like(like)))
    if status:
        stmt = stmt.where(Project.status == status)
    if client_id:
        stmt = stmt.where(Project.client_id == client_id)
    if owner_id:
        stmt = stmt.where(Project.owner_id == owner_id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(Project.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return ok(PageResult[ProjectOut](
        items=[ProjectOut.model_validate(r) for r in rows], page=page, page_size=page_size, total=total
    ))


@router.get("/{project_id}", response_model=ApiResponse[ProjectOut])
def get_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proj = db.get(Project, project_id)
    if not proj or proj.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="项目不存在")
    auth_ids = authorized_project_ids(user)
    if auth_ids is not None and project_id not in auth_ids:
        raise HTTPException(403, detail="无权访问该项目（未授权）")
    return ok(ProjectOut.model_validate(proj))


@router.post("", response_model=ApiResponse[ProjectOut])
def create_project(
    payload: ProjectCreate,
    user: User = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db),
):
    exists = db.execute(
        select(Project).where(Project.tenant_id == user.tenant_id, Project.code == payload.code)
    ).scalars().first()
    if exists:
        raise HTTPException(400, detail="项目编号已存在")
    proj = Project(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(proj)
    db.commit()
    db.refresh(proj)
    write_audit(db, user=user, action="create", target_type="project", target_id=proj.id)
    return ok(ProjectOut.model_validate(proj))


@router.put("/{project_id}", response_model=ApiResponse[ProjectOut])
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    user: User = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db),
):
    proj = db.get(Project, project_id)
    if not proj or proj.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="项目不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(proj, k, v)
    db.commit()
    db.refresh(proj)
    write_audit(db, user=user, action="update", target_type="project", target_id=proj.id)
    return ok(ProjectOut.model_validate(proj))


@router.delete("/{project_id}", response_model=ApiResponse[dict])
def delete_project(
    project_id: int,
    user: User = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db),
):
    proj = db.get(Project, project_id)
    if not proj or proj.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="项目不存在")
    db.delete(proj)
    db.commit()
    write_audit(db, user=user, action="delete", target_type="project", target_id=project_id)
    return ok({"success": True})
