"""第三方集成：短信 / 电子签 / OCR（Mock 可切换真实），全程留痕。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.models import IntegrationLog, User
from app.schemas.common import ApiResponse, PageResult, ok
from app.schemas.models import (
    ESignInitiateIn,
    IntegrationLogOut,
    IntegrationProviders,
    OcrRecognizeIn,
    SmsSendIn,
)
from app.services.integrations import (
    ProviderError,
    get_esign_provider,
    get_ocr_provider,
    get_sms_provider,
)

router = APIRouter(prefix="/integrations", tags=["第三方集成"])


def _log(db: Session, user: User, *, channel: str, provider: str, action: str,
         target: str | None, status: str, req: dict, resp: dict) -> None:
    db.add(IntegrationLog(
        tenant_id=user.tenant_id, channel=channel, provider=provider, action=action,
        target=target, status=status,
        request_summary=json.dumps(req, ensure_ascii=False)[:1000],
        response_summary=json.dumps(resp, ensure_ascii=False)[:1000],
        operator_id=user.id, operator_name=user.name,
    ))
    db.commit()


@router.get("/providers", response_model=ApiResponse[IntegrationProviders])
def providers(user: User = Depends(get_current_user)):
    return ok(IntegrationProviders(sms=settings.SMS_PROVIDER, esign=settings.ESIGN_PROVIDER, ocr=settings.OCR_PROVIDER))


@router.post("/sms", response_model=ApiResponse[dict])
def send_sms(
    payload: SmsSendIn,
    user: User = Depends(require_permission("integration:manage")),
    db: Session = Depends(get_db),
):
    try:
        provider = get_sms_provider()
        resp = provider.send(payload.to, payload.content)
        _log(db, user, channel="sms", provider=provider.name, action="send", target=payload.to,
             status="success", req=payload.model_dump(), resp=resp)
        return ok(resp)
    except ProviderError as e:
        _log(db, user, channel="sms", provider=settings.SMS_PROVIDER, action="send", target=payload.to,
             status="failed", req=payload.model_dump(), resp={"error": str(e)})
        raise HTTPException(501, detail=str(e))


@router.post("/esign", response_model=ApiResponse[dict])
def initiate_esign(
    payload: ESignInitiateIn,
    user: User = Depends(require_permission("integration:manage")),
    db: Session = Depends(get_db),
):
    try:
        provider = get_esign_provider()
        resp = provider.initiate(payload.doc_name, payload.signers)
        _log(db, user, channel="esign", provider=provider.name, action="initiate", target=payload.doc_name,
             status="success", req=payload.model_dump(), resp=resp)
        return ok(resp)
    except ProviderError as e:
        _log(db, user, channel="esign", provider=settings.ESIGN_PROVIDER, action="initiate", target=payload.doc_name,
             status="failed", req=payload.model_dump(), resp={"error": str(e)})
        raise HTTPException(501, detail=str(e))


@router.post("/ocr", response_model=ApiResponse[dict])
def ocr_recognize(
    doc_type: str = Form("invoice"),
    file: UploadFile | None = File(None),
    user: User = Depends(require_permission("integration:manage")),
    db: Session = Depends(get_db),
):
    filename = file.filename if file else "manual.png"
    content = file.file.read() if file else None
    try:
        provider = get_ocr_provider()
        resp = provider.recognize(filename or "file", doc_type, content)
        _log(db, user, channel="ocr", provider=provider.name, action="recognize", target=filename,
             status="success", req={"doc_type": doc_type, "filename": filename}, resp=resp)
        return ok(resp)
    except ProviderError as e:
        _log(db, user, channel="ocr", provider=settings.OCR_PROVIDER, action="recognize", target=filename,
             status="failed", req={"doc_type": doc_type, "filename": filename}, resp={"error": str(e)})
        raise HTTPException(501, detail=str(e))


@router.get("/logs", response_model=ApiResponse[PageResult[IntegrationLogOut]])
def list_logs(
    channel: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(IntegrationLog).where(IntegrationLog.tenant_id == user.tenant_id)
    if channel:
        stmt = stmt.where(IntegrationLog.channel == channel)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(IntegrationLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return ok(PageResult[IntegrationLogOut](
        items=[IntegrationLogOut.model_validate(r) for r in rows], page=page, page_size=page_size, total=total
    ))
