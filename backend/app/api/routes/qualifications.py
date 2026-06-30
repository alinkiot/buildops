"""资质合规：资质台账 CRUD + 核验记录 + 到期扫描自动生成预警（R-001）。"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission, write_audit
from app.db.session import get_db
from app.models import Alert, Qualification, QualificationVerifyRecord, User
from app.models.enums import (
    AlertLevel,
    AlertSource,
    AlertStatus,
    QualificationStatus,
    VerifyStatus,
)
from app.schemas.common import ApiResponse, PageResult, ok
from app.schemas.models import (
    QualificationCreate,
    QualificationOut,
    QualificationUpdate,
    ScanResult,
    VerifyRecordCreate,
    VerifyRecordOut,
)

router = APIRouter(prefix="/qualifications", tags=["资质合规"])

EXPIRING_DAYS = 90  # 到期提醒窗口


def _to_out(q: Qualification) -> QualificationOut:
    out = QualificationOut.model_validate(q)
    if q.valid_to:
        out.days_to_expire = (q.valid_to - date.today()).days
    return out


@router.get("", response_model=ApiResponse[PageResult[QualificationOut]])
def list_qualifications(
    keyword: str | None = Query(None),
    status: QualificationStatus | None = Query(None),
    verify_status: VerifyStatus | None = Query(None),
    type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Qualification).where(Qualification.tenant_id == user.tenant_id)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where((Qualification.name.like(like)) | (Qualification.cert_no.like(like)))
    if status:
        stmt = stmt.where(Qualification.status == status)
    if verify_status:
        stmt = stmt.where(Qualification.verify_status == verify_status)
    if type:
        stmt = stmt.where(Qualification.type == type)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(Qualification.valid_to.asc().nulls_last()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return ok(PageResult[QualificationOut](
        items=[_to_out(r) for r in rows], page=page, page_size=page_size, total=total
    ))


@router.get("/{qid}", response_model=ApiResponse[QualificationOut])
def get_qualification(qid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.get(Qualification, qid)
    if not q or q.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="资质不存在")
    return ok(_to_out(q))


@router.post("", response_model=ApiResponse[QualificationOut])
def create_qualification(
    payload: QualificationCreate,
    user: User = Depends(require_permission("qualification:manage")),
    db: Session = Depends(get_db),
):
    q = Qualification(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(q)
    db.commit()
    db.refresh(q)
    write_audit(db, user=user, action="create", target_type="qualification", target_id=q.id)
    return ok(_to_out(q))


@router.put("/{qid}", response_model=ApiResponse[QualificationOut])
def update_qualification(
    qid: int,
    payload: QualificationUpdate,
    user: User = Depends(require_permission("qualification:manage")),
    db: Session = Depends(get_db),
):
    q = db.get(Qualification, qid)
    if not q or q.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="资质不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(q, k, v)
    db.commit()
    db.refresh(q)
    write_audit(db, user=user, action="update", target_type="qualification", target_id=q.id)
    return ok(_to_out(q))


@router.delete("/{qid}", response_model=ApiResponse[dict])
def delete_qualification(
    qid: int,
    user: User = Depends(require_permission("qualification:manage")),
    db: Session = Depends(get_db),
):
    q = db.get(Qualification, qid)
    if not q or q.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="资质不存在")
    db.delete(q)
    db.commit()
    write_audit(db, user=user, action="delete", target_type="qualification", target_id=qid)
    return ok({"success": True})


# ---------------- 核验记录 ----------------
@router.get("/{qid}/verify-records", response_model=ApiResponse[list[VerifyRecordOut]])
def list_verify_records(qid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.get(Qualification, qid)
    if not q or q.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="资质不存在")
    rows = db.execute(
        select(QualificationVerifyRecord)
        .where(QualificationVerifyRecord.qualification_id == qid)
        .order_by(QualificationVerifyRecord.id.desc())
    ).scalars().all()
    return ok([VerifyRecordOut.model_validate(r) for r in rows])


@router.post("/{qid}/verify", response_model=ApiResponse[VerifyRecordOut])
def verify_qualification(
    qid: int,
    payload: VerifyRecordCreate,
    user: User = Depends(require_permission("qualification:manage")),
    db: Session = Depends(get_db),
):
    q = db.get(Qualification, qid)
    if not q or q.tenant_id != user.tenant_id:
        raise HTTPException(404, detail="资质不存在")
    record = QualificationVerifyRecord(
        tenant_id=user.tenant_id,
        qualification_id=qid,
        result=payload.result,
        method=payload.method,
        remark=payload.remark,
        operator_id=user.id,
        operator_name=user.name,
    )
    db.add(record)
    # 同步资质核验状态
    q.verify_status = payload.result
    if payload.result == VerifyStatus.VERIFIED and q.status == QualificationStatus.PENDING_VERIFY:
        q.status = QualificationStatus.VALID
    db.commit()
    db.refresh(record)
    write_audit(db, user=user, action="verify", target_type="qualification", target_id=qid,
                detail=f"result={payload.result.value}")
    return ok(VerifyRecordOut.model_validate(record))


# ---------------- 到期扫描生成预警 ----------------
@router.post("/scan", response_model=ApiResponse[ScanResult])
def scan_expiry(
    user: User = Depends(require_permission("qualification:manage")),
    db: Session = Depends(get_db),
):
    """扫描资质有效期：更新状态并为即将到期/已过期资质生成预警（去重）。"""
    today = date.today()
    quals = db.execute(
        select(Qualification).where(Qualification.tenant_id == user.tenant_id)
    ).scalars().all()

    expiring = expired = alerts_created = 0
    for q in quals:
        if q.status == QualificationStatus.DISABLED or not q.valid_to:
            continue
        days = (q.valid_to - today).days
        if days < 0:
            new_status = QualificationStatus.EXPIRED
            level = AlertLevel.CRITICAL
            msg = f"已过期 {abs(days)} 天"
            expired += 1
        elif days <= EXPIRING_DAYS:
            new_status = QualificationStatus.EXPIRING
            level = AlertLevel.HIGH
            msg = f"将于 {days} 天后到期"
            expiring += 1
        else:
            # 仍在有效期内，恢复为有效
            if q.status in (QualificationStatus.EXPIRING, QualificationStatus.EXPIRED):
                q.status = QualificationStatus.VALID
            continue

        q.status = new_status
        title = f"资质『{q.name}』{msg}"
        # 去重：同名未关闭预警不重复创建
        dup = db.execute(
            select(Alert).where(
                Alert.tenant_id == user.tenant_id,
                Alert.source == AlertSource.QUALIFICATION,
                Alert.title == title,
                Alert.status != AlertStatus.CLOSED,
            )
        ).scalars().first()
        if not dup:
            db.add(Alert(
                tenant_id=user.tenant_id,
                source=AlertSource.QUALIFICATION,
                title=title,
                level=level,
                owner_id=q.owner_id or user.id,
                due_date=q.valid_to,
                status=AlertStatus.PENDING,
            ))
            alerts_created += 1

    db.commit()
    write_audit(db, user=user, action="scan", target_type="qualification",
                detail=f"expiring={expiring},expired={expired},alerts={alerts_created}")
    return ok(ScanResult(scanned=len(quals), expiring=expiring, expired=expired, alerts_created=alerts_created))
