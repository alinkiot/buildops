"""数据导出：关键列表导出为 CSV（带 UTF-8 BOM，Excel 友好）。"""
from __future__ import annotations

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, write_audit
from app.db.session import get_db
from app.models import Alert, Project, Receivable, User
from app.models.enums import ReceivableStatus

router = APIRouter(prefix="/export", tags=["数据导出"])

_PROJECT_STATUS = {
    "preparing": "筹备", "ongoing": "在建", "suspended": "停工", "completed": "竣工",
    "settling": "结算中", "collecting": "清欠中", "archived": "归档",
}
_DEBT_TYPE = {"progress": "进度款", "final": "竣工尾款", "warranty": "质保金", "advance": "垫资款", "other": "其他"}
_RECV_STATUS = {
    "normal": "正常回款", "overdue": "逾期", "stagnant": "呆滞", "bad_debt_risk": "坏账风险",
    "legal_process": "诉讼处理中", "partial": "部分回款", "settled": "已结清", "written_off": "已核销",
}
_ALERT_SOURCE = {"qualification": "资质", "document": "资料", "cost": "成本", "finance": "财税", "receivable": "回款", "secret": "涉密", "bid": "招投标", "labor": "劳务"}
_ALERT_LEVEL = {"low": "一般", "medium": "关注", "high": "预警", "critical": "高风险"}
_ALERT_STATUS = {"pending": "待处理", "processing": "处理中", "closed": "已关闭", "overdue": "已逾期", "escalated": "已升级"}


def _csv_response(filename: str, headers: list[str], rows: list[list]) -> StreamingResponse:
    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM，便于 Excel 正确识别中文
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/projects")
def export_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Project).where(Project.tenant_id == user.tenant_id).order_by(Project.id)
    ).scalars().all()
    data = [
        [
            p.code, p.name, p.type or "", p.region or "",
            p.owner.name if p.owner else "", p.client.name if p.client else "",
            f"{float(p.contract_amount):.2f}", f"{float(p.received_amount):.2f}", f"{float(p.cost_amount):.2f}",
            f"{float(p.contract_amount) - float(p.received_amount):.2f}",
            p.start_date.isoformat() if p.start_date else "",
            p.plan_end_date.isoformat() if p.plan_end_date else "",
            _PROJECT_STATUS.get(p.status.value, p.status.value),
        ]
        for p in rows
    ]
    write_audit(db, user=user, action="export", target_type="project", detail=f"count={len(data)}")
    return _csv_response(
        "projects.csv",
        ["项目编号", "项目名称", "类型", "地域", "负责人", "甲方", "合同额", "已回款", "成本", "待回款", "开工日期", "计划竣工", "状态"],
        data,
    )


@router.get("/receivables")
def export_receivables(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Receivable).where(Receivable.tenant_id == user.tenant_id).order_by(Receivable.id)
    ).scalars().all()
    today = date.today()
    data = []
    for r in rows:
        out = float(r.amount) - float(r.received_amount)
        od = 0
        if r.due_date and r.status not in (ReceivableStatus.SETTLED, ReceivableStatus.WRITTEN_OFF) and out > 0:
            od = max(0, (today - r.due_date).days)
        data.append([
            r.client.name if r.client else "", r.project.name if r.project else "",
            _DEBT_TYPE.get(r.debt_type.value, r.debt_type.value), r.contract_no or "",
            f"{float(r.amount):.2f}", f"{float(r.received_amount):.2f}", f"{out:.2f}",
            r.due_date.isoformat() if r.due_date else "", str(od),
            r.stage or "", _RECV_STATUS.get(r.status.value, r.status.value),
        ])
    write_audit(db, user=user, action="export", target_type="receivable", detail=f"count={len(data)}")
    return _csv_response(
        "receivables.csv",
        ["甲方", "项目", "欠款类型", "合同编号", "欠款金额", "已回款", "待回款", "到期日", "逾期天数", "催收阶段", "状态"],
        data,
    )


@router.get("/alerts")
def export_alerts(
    source: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Alert).where(Alert.tenant_id == user.tenant_id)
    if source:
        stmt = stmt.where(Alert.source == source)
    rows = db.execute(stmt.order_by(Alert.id.desc())).scalars().all()
    data = [
        [
            str(a.id), a.title, _ALERT_SOURCE.get(a.source.value, a.source.value),
            a.project.name if a.project else "", _ALERT_LEVEL.get(a.level.value, a.level.value),
            a.owner.name if a.owner else "", a.due_date.isoformat() if a.due_date else "",
            _ALERT_STATUS.get(a.status.value, a.status.value),
            a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
        ]
        for a in rows
    ]
    write_audit(db, user=user, action="export", target_type="alert", detail=f"count={len(data)}")
    return _csv_response(
        "alerts.csv",
        ["编号", "预警标题", "来源", "关联项目", "等级", "责任人", "截止日期", "状态", "创建时间"],
        data,
    )
