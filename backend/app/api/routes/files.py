"""文件中心：上传、列表、下载、版本、密级、日志。"""
from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission, write_audit
from app.core.config import settings
from app.db.session import get_db
from app.models import FileObject, User
from app.models.enums import FileStatus, SecretLevel
from app.schemas.common import ApiResponse, PageResult, ok
from app.schemas.models import FileOut, FileUpdate

router = APIRouter(prefix="/files", tags=["文件中心"])


@router.get("", response_model=ApiResponse[PageResult[FileOut]])
def list_files(
    keyword: str | None = Query(None),
    project_id: int | None = Query(None),
    business_type: str | None = Query(None),
    secret_level: SecretLevel | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(FileObject).where(
        FileObject.tenant_id == user.tenant_id, FileObject.status != FileStatus.DELETED
    )
    if keyword:
        stmt = stmt.where(FileObject.name.like(f"%{keyword}%"))
    if project_id:
        stmt = stmt.where(FileObject.project_id == project_id)
    if business_type:
        stmt = stmt.where(FileObject.business_type == business_type)
    if secret_level:
        stmt = stmt.where(FileObject.secret_level == secret_level)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(FileObject.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return ok(PageResult[FileOut](
        items=[FileOut.model_validate(r) for r in rows], page=page, page_size=page_size, total=total
    ))


@router.post("/upload", response_model=ApiResponse[FileOut])
def upload_file(
    file: UploadFile = File(...),
    business_type: str | None = Form(None),
    project_id: int | None = Form(None),
    secret_level: SecretLevel = Form(SecretLevel.INTERNAL),
    user: User = Depends(require_permission("file:manage")),
    db: Session = Depends(get_db),
):
    tenant_dir = os.path.join(settings.UPLOAD_DIR, str(user.tenant_id))
    os.makedirs(tenant_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    storage_path = os.path.join(tenant_dir, stored_name)
    size = 0
    with open(storage_path, "wb") as f:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            f.write(chunk)

    obj = FileObject(
        tenant_id=user.tenant_id,
        name=file.filename or stored_name,
        business_type=business_type,
        project_id=project_id,
        size=size,
        content_type=file.content_type,
        secret_level=secret_level,
        uploader_id=user.id,
        storage_path=storage_path,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    write_audit(db, user=user, action="upload", target_type="file", target_id=obj.id, detail=obj.name)
    return ok(FileOut.model_validate(obj))


@router.get("/{file_id}/download")
def download_file(file_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    obj = db.get(FileObject, file_id)
    if not obj or obj.tenant_id != user.tenant_id or obj.status == FileStatus.DELETED:
        raise HTTPException(404, detail="文件不存在")
    # 涉密文件需具备涉密查看权限
    if obj.secret_level == SecretLevel.CLASSIFIED and not user.is_superadmin:
        from app.api.deps import collect_permissions

        if "file:classified:view" not in collect_permissions(user):
            raise HTTPException(403, detail="无权访问涉密文件")
    if not os.path.exists(obj.storage_path):
        raise HTTPException(404, detail="文件已丢失")
    obj.download_count += 1
    db.commit()
    write_audit(db, user=user, action="download", target_type="file", target_id=obj.id, detail=obj.name)
    return FileResponse(obj.storage_path, filename=obj.name, media_type=obj.content_type or "application/octet-stream")


# 可在线预览的内容类型（PDF / 常见图片）
_PREVIEWABLE = ("application/pdf", "image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp", "text/plain")


@router.get("/{file_id}/preview")
def preview_file(file_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """在线预览：以 inline 方式返回 PDF/图片/文本，浏览器内打开。"""
    obj = db.get(FileObject, file_id)
    if not obj or obj.tenant_id != user.tenant_id or obj.status == FileStatus.DELETED:
        raise HTTPException(404, detail="文件不存在")
    if obj.secret_level == SecretLevel.CLASSIFIED and not user.is_superadmin:
        from app.api.deps import collect_permissions

        if "file:classified:view" not in collect_permissions(user):
            raise HTTPException(403, detail="无权预览涉密文件")
    ctype = (obj.content_type or "").lower()
    if not any(ctype.startswith(t) for t in _PREVIEWABLE):
        raise HTTPException(415, detail="该文件类型暂不支持在线预览，请下载查看")
    if not os.path.exists(obj.storage_path):
        raise HTTPException(404, detail="文件已丢失")
    write_audit(db, user=user, action="preview", target_type="file", target_id=obj.id, detail=obj.name)
    # inline 展示而非下载
    return FileResponse(
        obj.storage_path,
        filename=obj.name,
        media_type=obj.content_type or "application/octet-stream",
        content_disposition_type="inline",
    )


@router.put("/{file_id}", response_model=ApiResponse[FileOut])
def update_file(
    file_id: int,
    payload: FileUpdate,
    user: User = Depends(require_permission("file:manage")),
    db: Session = Depends(get_db),
):
    obj = db.get(FileObject, file_id)
    if not obj or obj.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="文件不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    write_audit(db, user=user, action="update", target_type="file", target_id=obj.id)
    return ok(FileOut.model_validate(obj))


@router.delete("/{file_id}", response_model=ApiResponse[dict])
def delete_file(
    file_id: int,
    user: User = Depends(require_permission("file:manage")),
    db: Session = Depends(get_db),
):
    obj = db.get(FileObject, file_id)
    if not obj or obj.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="文件不存在")
    obj.status = FileStatus.DELETED
    db.commit()
    write_audit(db, user=user, action="delete", target_type="file", target_id=obj.id)
    return ok({"success": True})
