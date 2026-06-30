"""工程资料：模板库、清单生成、上传、审核、缺项扫描(R-005)、完整度、组卷。"""
from __future__ import annotations

import os
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ensure_project_visible, get_current_user, require_permission, write_audit
from app.core.config import settings
from app.db.session import get_db
from app.models import (
    Alert,
    DocItem,
    DocTemplate,
    FileObject,
    Project,
    User,
)
from app.models.enums import AlertLevel, AlertSource, AlertStatus, DocStatus, SecretLevel
from app.schemas.common import ApiResponse, PageResult, ok
from app.schemas.models import (
    ApplyTemplateRequest,
    ArchiveResult,
    CompletenessOut,
    DocItemCreate,
    DocItemOut,
    DocItemUpdate,
    DocReview,
    DocScanResult,
    DocTemplateIn,
    DocTemplateOut,
)

router = APIRouter(prefix="/documents", tags=["工程资料"])

_OPEN_FOR_MISSING = (DocStatus.PENDING_UPLOAD, DocStatus.RETURNED)


def _to_out(item: DocItem) -> DocItemOut:
    out = DocItemOut.model_validate(item)
    out.overdue = bool(
        item.due_date and item.due_date < date.today() and item.status != DocStatus.APPROVED
        and item.status != DocStatus.ARCHIVED
    )
    return out


def _check_project(db: Session, user: User, project_id: int) -> Project:
    proj = db.get(Project, project_id)
    if not proj or proj.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="项目不存在")
    if not ensure_project_visible(user, project_id):
        raise HTTPException(403, detail="无权访问该项目（未授权）")
    return proj


# ---------------- 模板库 ----------------
@router.get("/templates", response_model=ApiResponse[list[DocTemplateOut]])
def list_templates(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(DocTemplate).where(DocTemplate.tenant_id == user.tenant_id).order_by(DocTemplate.sort, DocTemplate.id)
    ).scalars().all()
    return ok([DocTemplateOut.model_validate(r) for r in rows])


@router.post("/templates", response_model=ApiResponse[DocTemplateOut])
def create_template(
    payload: DocTemplateIn,
    user: User = Depends(require_permission("document:manage")),
    db: Session = Depends(get_db),
):
    tpl = DocTemplate(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    write_audit(db, user=user, action="create", target_type="doc_template", target_id=tpl.id)
    return ok(DocTemplateOut.model_validate(tpl))


@router.put("/templates/{tid}", response_model=ApiResponse[DocTemplateOut])
def update_template(
    tid: int,
    payload: DocTemplateIn,
    user: User = Depends(require_permission("document:manage")),
    db: Session = Depends(get_db),
):
    tpl = db.get(DocTemplate, tid)
    if not tpl or tpl.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="模板不存在")
    for k, v in payload.model_dump().items():
        setattr(tpl, k, v)
    db.commit()
    db.refresh(tpl)
    return ok(DocTemplateOut.model_validate(tpl))


@router.delete("/templates/{tid}", response_model=ApiResponse[dict])
def delete_template(
    tid: int,
    user: User = Depends(require_permission("document:manage")),
    db: Session = Depends(get_db),
):
    tpl = db.get(DocTemplate, tid)
    if not tpl or tpl.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="模板不存在")
    db.delete(tpl)
    db.commit()
    return ok({"success": True})


@router.post("/apply-template", response_model=ApiResponse[dict])
def apply_template(
    payload: ApplyTemplateRequest,
    user: User = Depends(require_permission("document:manage")),
    db: Session = Depends(get_db),
):
    """按模板为项目生成资料清单条目（已存在同名条目则跳过）。"""
    _check_project(db, user, payload.project_id)
    stmt = select(DocTemplate).where(DocTemplate.tenant_id == user.tenant_id)
    if payload.template_ids:
        stmt = stmt.where(DocTemplate.id.in_(payload.template_ids))
    templates = db.execute(stmt).scalars().all()

    existing = {
        n for (n,) in db.execute(
            select(DocItem.name).where(DocItem.project_id == payload.project_id)
        ).all()
    }
    created = 0
    for tpl in templates:
        if tpl.name in existing:
            continue
        db.add(DocItem(
            tenant_id=user.tenant_id,
            project_id=payload.project_id,
            name=tpl.name,
            category=tpl.category,
            specialty=tpl.specialty,
            stage=tpl.stage,
            required=tpl.required,
            due_date=payload.default_due_date,
            status=DocStatus.PENDING_UPLOAD,
        ))
        created += 1
    db.commit()
    write_audit(db, user=user, action="apply_template", target_type="project",
                target_id=payload.project_id, detail=f"created={created}")
    return ok({"created": created, "templates": len(templates)})


# ---------------- 资料条目 ----------------
@router.get("", response_model=ApiResponse[PageResult[DocItemOut]])
def list_items(
    project_id: int = Query(...),
    status: DocStatus | None = Query(None),
    stage: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_project(db, user, project_id)
    stmt = select(DocItem).where(DocItem.tenant_id == user.tenant_id, DocItem.project_id == project_id)
    if status:
        stmt = stmt.where(DocItem.status == status)
    if stage:
        stmt = stmt.where(DocItem.stage == stage)
    if keyword:
        stmt = stmt.where(DocItem.name.like(f"%{keyword}%"))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(DocItem.stage, DocItem.id).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return ok(PageResult[DocItemOut](
        items=[_to_out(r) for r in rows], page=page, page_size=page_size, total=total
    ))


@router.post("", response_model=ApiResponse[DocItemOut])
def create_item(
    payload: DocItemCreate,
    user: User = Depends(require_permission("document:manage")),
    db: Session = Depends(get_db),
):
    _check_project(db, user, payload.project_id)
    item = DocItem(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    write_audit(db, user=user, action="create", target_type="doc_item", target_id=item.id)
    return ok(_to_out(item))


@router.put("/{item_id}", response_model=ApiResponse[DocItemOut])
def update_item(
    item_id: int,
    payload: DocItemUpdate,
    user: User = Depends(require_permission("document:manage")),
    db: Session = Depends(get_db),
):
    item = db.get(DocItem, item_id)
    if not item or item.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="资料条目不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return ok(_to_out(item))


@router.delete("/{item_id}", response_model=ApiResponse[dict])
def delete_item(
    item_id: int,
    user: User = Depends(require_permission("document:manage")),
    db: Session = Depends(get_db),
):
    item = db.get(DocItem, item_id)
    if not item or item.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="资料条目不存在")
    db.delete(item)
    db.commit()
    write_audit(db, user=user, action="delete", target_type="doc_item", target_id=item_id)
    return ok({"success": True})


@router.post("/{item_id}/upload", response_model=ApiResponse[DocItemOut])
def upload_item_file(
    item_id: int,
    file: UploadFile = File(...),
    user: User = Depends(require_permission("document:manage")),
    db: Session = Depends(get_db),
):
    item = db.get(DocItem, item_id)
    if not item or item.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="资料条目不存在")

    tenant_dir = os.path.join(settings.UPLOAD_DIR, str(user.tenant_id), "documents")
    os.makedirs(tenant_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1]
    stored = os.path.join(tenant_dir, f"{uuid.uuid4().hex}{ext}")
    size = 0
    with open(stored, "wb") as f:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            f.write(chunk)

    obj = FileObject(
        tenant_id=user.tenant_id,
        name=file.filename or "resource",
        business_type="工程资料",
        project_id=item.project_id,
        size=size,
        content_type=file.content_type,
        secret_level=item.secret_level,
        uploader_id=user.id,
        storage_path=stored,
    )
    db.add(obj)
    db.flush()

    item.file_id = obj.id
    item.version += 1
    item.uploader_id = user.id
    item.status = DocStatus.PENDING_REVIEW
    db.commit()
    db.refresh(item)
    write_audit(db, user=user, action="upload", target_type="doc_item", target_id=item.id, detail=obj.name)
    return ok(_to_out(item))


@router.post("/{item_id}/review", response_model=ApiResponse[DocItemOut])
def review_item(
    item_id: int,
    payload: DocReview,
    user: User = Depends(require_permission("document:review")),
    db: Session = Depends(get_db),
):
    item = db.get(DocItem, item_id)
    if not item or item.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="资料条目不存在")
    if item.status not in (DocStatus.PENDING_REVIEW, DocStatus.RETURNED, DocStatus.APPROVED):
        raise HTTPException(400, detail="该状态不可审核，请先上传资料")
    item.status = DocStatus.APPROVED if payload.approved else DocStatus.RETURNED
    item.reviewer_id = user.id
    item.review_remark = payload.review_remark
    db.commit()
    db.refresh(item)
    write_audit(db, user=user, action="review", target_type="doc_item", target_id=item.id,
                detail="approved" if payload.approved else "returned")
    return ok(_to_out(item))


# ---------------- 缺项扫描（R-005） ----------------
@router.post("/scan", response_model=ApiResponse[DocScanResult])
def scan_missing(
    project_id: int = Query(...),
    user: User = Depends(require_permission("document:manage")),
    db: Session = Depends(get_db),
):
    """扫描逾期未交资料，标记缺项并生成预警（R-005）。"""
    _check_project(db, user, project_id)
    today = date.today()
    items = db.execute(
        select(DocItem).where(DocItem.tenant_id == user.tenant_id, DocItem.project_id == project_id)
    ).scalars().all()

    missing = alerts = 0
    for it in items:
        if not it.required or not it.due_date:
            continue
        if it.due_date < today and it.status in _OPEN_FOR_MISSING:
            it.status = DocStatus.MISSING
            missing += 1
            title = f"资料缺项：『{it.name}』已逾期未提交"
            dup = db.execute(
                select(Alert).where(
                    Alert.tenant_id == user.tenant_id,
                    Alert.source == AlertSource.DOCUMENT,
                    Alert.project_id == project_id,
                    Alert.title == title,
                    Alert.status != AlertStatus.CLOSED,
                )
            ).scalars().first()
            if not dup:
                db.add(Alert(
                    tenant_id=user.tenant_id,
                    source=AlertSource.DOCUMENT,
                    title=title,
                    project_id=project_id,
                    level=AlertLevel.MEDIUM,
                    owner_id=it.uploader_id or user.id,
                    due_date=it.due_date,
                    status=AlertStatus.PENDING,
                ))
                alerts += 1
    db.commit()
    write_audit(db, user=user, action="scan", target_type="project", target_id=project_id,
                detail=f"missing={missing},alerts={alerts}")
    return ok(DocScanResult(scanned=len(items), missing=missing, alerts_created=alerts))


# ---------------- 完整度统计 ----------------
@router.get("/completeness", response_model=ApiResponse[CompletenessOut])
def completeness(
    project_id: int = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_project(db, user, project_id)
    items = db.execute(
        select(DocItem).where(DocItem.tenant_id == user.tenant_id, DocItem.project_id == project_id)
    ).scalars().all()
    required_total = sum(1 for i in items if i.required)
    approved = sum(1 for i in items if i.status in (DocStatus.APPROVED, DocStatus.ARCHIVED))
    approved_required = sum(1 for i in items if i.required and i.status in (DocStatus.APPROVED, DocStatus.ARCHIVED))
    return ok(CompletenessOut(
        project_id=project_id,
        total=len(items),
        required_total=required_total,
        approved=approved,
        pending_upload=sum(1 for i in items if i.status == DocStatus.PENDING_UPLOAD),
        pending_review=sum(1 for i in items if i.status == DocStatus.PENDING_REVIEW),
        returned=sum(1 for i in items if i.status == DocStatus.RETURNED),
        missing=sum(1 for i in items if i.status == DocStatus.MISSING),
        completeness=round(approved_required / required_total * 100, 1) if required_total else 0.0,
    ))


# ---------------- 组卷 ----------------
@router.post("/archive", response_model=ApiResponse[ArchiveResult])
def archive(
    project_id: int = Query(...),
    user: User = Depends(require_permission("document:manage")),
    db: Session = Depends(get_db),
):
    """竣工组卷：将已通过资料归档并输出组卷清单。"""
    _check_project(db, user, project_id)
    items = db.execute(
        select(DocItem).where(
            DocItem.tenant_id == user.tenant_id,
            DocItem.project_id == project_id,
            DocItem.status == DocStatus.APPROVED,
        )
    ).scalars().all()
    manifest = []
    for idx, it in enumerate(items, 1):
        it.status = DocStatus.ARCHIVED
        manifest.append({
            "no": idx,
            "name": it.name,
            "stage": it.stage,
            "specialty": it.specialty,
            "version": it.version,
            "file_id": it.file_id,
        })
    db.commit()
    write_audit(db, user=user, action="archive", target_type="project", target_id=project_id,
                detail=f"archived={len(manifest)}")
    return ok(ArchiveResult(archived=len(manifest), manifest=manifest))
