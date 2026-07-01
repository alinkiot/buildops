"""SQLAlchemy 数据模型（首期：底座 + 项目 + 文件 + 预警）。"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Column,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import (
    AlertLevel,
    AlertSource,
    AlertStatus,
    CollectionLogType,
    CommonStatus,
    DataScope,
    DebtType,
    DocStatus,
    ExpenseStatus,
    ExpenseType,
    FeedbackStatus,
    FileStatus,
    FinanceDirection,
    FinanceStatus,
    ProjectStatus,
    QualificationStatus,
    ReceivableStatus,
    SecretLevel,
    TenderStatus,
    VerifyStatus,
    WorkerStatus,
)


def _enum(enum_cls):
    """统一以枚举 value 落库，兼容各数据库。"""
    return SAEnum(enum_cls, values_callable=lambda e: [m.value for m in e], native_enum=False, length=32)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


# ---------------- 关联表 ----------------
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_code", ForeignKey("permissions.code", ondelete="CASCADE"), primary_key=True),
)

user_projects = Table(
    "user_projects",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
)


# ---------------- 底座 ----------------
class Tenant(TimestampMixin, Base):
    """租户企业。"""
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    credit_code: Mapped[str | None] = mapped_column(String(64))
    region: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[CommonStatus] = mapped_column(_enum(CommonStatus), default=CommonStatus.ENABLED)


class Department(TimestampMixin, Base):
    """组织/部门。"""
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Role(TimestampMixin, Base):
    """角色。"""
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_role_tenant_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    data_scope: Mapped[DataScope] = mapped_column(_enum(DataScope), default=DataScope.SELF)
    remark: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[CommonStatus] = mapped_column(_enum(CommonStatus), default=CommonStatus.ENABLED)

    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permissions, lazy="selectin"
    )


class Permission(Base):
    """菜单/按钮权限定义（全局）。"""
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[str] = mapped_column(String(16), default="menu")  # menu / button
    parent_code: Mapped[str | None] = mapped_column(String(64))
    path: Mapped[str | None] = mapped_column(String(128))
    sort: Mapped[int] = mapped_column(Integer, default=0)


class User(TimestampMixin, Base):
    """用户账号。"""
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "username", name="uq_user_tenant_username"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(128))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    status: Mapped[CommonStatus] = mapped_column(_enum(CommonStatus), default=CommonStatus.ENABLED)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)

    roles: Mapped[list[Role]] = relationship(secondary=user_roles, lazy="selectin")
    department: Mapped[Department | None] = relationship(lazy="selectin")
    projects: Mapped[list["Project"]] = relationship(secondary=user_projects, lazy="selectin")


class AuditLog(Base):
    """操作审计日志。"""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer)
    username: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)


# ---------------- 项目中心 ----------------
class ClientUnit(TimestampMixin, Base):
    """甲方单位。"""
    __tablename__ = "client_units"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    contact: Mapped[str | None] = mapped_column(String(64))
    phone: Mapped[str | None] = mapped_column(String(32))
    credit_rating: Mapped[str | None] = mapped_column(String(16))  # A/B/C/D
    remark: Mapped[str | None] = mapped_column(String(255))


class Project(TimestampMixin, Base):
    """项目。"""
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_project_tenant_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    type: Mapped[str | None] = mapped_column(String(64))
    region: Mapped[str | None] = mapped_column(String(64))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    client_id: Mapped[int | None] = mapped_column(ForeignKey("client_units.id"))
    contract_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    received_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    cost_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    start_date: Mapped[date | None] = mapped_column(Date)
    plan_end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[ProjectStatus] = mapped_column(_enum(ProjectStatus), default=ProjectStatus.PREPARING)
    secret_level: Mapped[SecretLevel] = mapped_column(_enum(SecretLevel), default=SecretLevel.INTERNAL)
    remark: Mapped[str | None] = mapped_column(Text)

    owner: Mapped[User | None] = relationship(lazy="selectin", foreign_keys=[owner_id])
    client: Mapped[ClientUnit | None] = relationship(lazy="selectin")


# ---------------- 文件中心 ----------------
class FileObject(TimestampMixin, Base):
    """文件对象。"""
    __tablename__ = "file_objects"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_type: Mapped[str | None] = mapped_column(String(64))  # 合同/图纸/票据/资质...
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    size: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), default=0)
    content_type: Mapped[str | None] = mapped_column(String(128))
    secret_level: Mapped[SecretLevel] = mapped_column(_enum(SecretLevel), default=SecretLevel.INTERNAL)
    uploader_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[FileStatus] = mapped_column(_enum(FileStatus), default=FileStatus.ACTIVE)

    project: Mapped[Project | None] = relationship(lazy="selectin")
    uploader: Mapped[User | None] = relationship(lazy="selectin")


# ---------------- 预警中心 ----------------
class AlertRule(TimestampMixin, Base):
    """预警规则。"""
    __tablename__ = "alert_rules"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_rule_tenant_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[AlertSource] = mapped_column(_enum(AlertSource))
    level: Mapped[AlertLevel] = mapped_column(_enum(AlertLevel), default=AlertLevel.MEDIUM)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[str | None] = mapped_column(String(255))


class Alert(TimestampMixin, Base):
    """预警事项。"""
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("alert_rules.id"))
    source: Mapped[AlertSource] = mapped_column(_enum(AlertSource))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    level: Mapped[AlertLevel] = mapped_column(_enum(AlertLevel), default=AlertLevel.MEDIUM)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[AlertStatus] = mapped_column(_enum(AlertStatus), default=AlertStatus.PENDING)
    handle_remark: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    project: Mapped[Project | None] = relationship(lazy="selectin")
    owner: Mapped[User | None] = relationship(lazy="selectin")


# ---------------- 资质合规 ----------------
class Qualification(TimestampMixin, Base):
    """资质证书台账。"""
    __tablename__ = "qualifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    type: Mapped[str | None] = mapped_column(String(64))            # 资质类型
    level: Mapped[str | None] = mapped_column(String(64))           # 等级
    cert_no: Mapped[str | None] = mapped_column(String(128))        # 证书编号
    issuing_authority: Mapped[str | None] = mapped_column(String(128))  # 发证机关
    scope: Mapped[str | None] = mapped_column(Text)                 # 承接范围
    region_limit: Mapped[str | None] = mapped_column(String(128))   # 地域限制
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)             # 有效期至
    annual_review_date: Mapped[date | None] = mapped_column(Date)   # 年审日期
    verify_status: Mapped[VerifyStatus] = mapped_column(_enum(VerifyStatus), default=VerifyStatus.UNVERIFIED)
    status: Mapped[QualificationStatus] = mapped_column(_enum(QualificationStatus), default=QualificationStatus.VALID)
    secret_level: Mapped[SecretLevel] = mapped_column(_enum(SecretLevel), default=SecretLevel.INTERNAL)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    file_id: Mapped[int | None] = mapped_column(ForeignKey("file_objects.id"))  # 证书扫描件
    remark: Mapped[str | None] = mapped_column(Text)

    owner: Mapped["User | None"] = relationship(lazy="selectin")


class QualificationVerifyRecord(Base):
    """资质核验记录。"""
    __tablename__ = "qualification_verify_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    qualification_id: Mapped[int] = mapped_column(ForeignKey("qualifications.id", ondelete="CASCADE"), index=True)
    result: Mapped[VerifyStatus] = mapped_column(_enum(VerifyStatus))
    method: Mapped[str | None] = mapped_column(String(64))          # 官网核验/人工核验
    remark: Mapped[str | None] = mapped_column(Text)
    operator_id: Mapped[int | None] = mapped_column(Integer)
    operator_name: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


# ---------------- 工程资料 ----------------
class DocTemplate(TimestampMixin, Base):
    """资料模板（标准资料清单条目库）。"""
    __tablename__ = "doc_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64))   # 资料类型
    specialty: Mapped[str | None] = mapped_column(String(64))  # 专业
    stage: Mapped[str | None] = mapped_column(String(64))      # 项目阶段
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    remark: Mapped[str | None] = mapped_column(String(255))


class DocItem(TimestampMixin, Base):
    """项目资料条目（资料目录/清单的一项）。"""
    __tablename__ = "doc_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64))
    specialty: Mapped[str | None] = mapped_column(String(64))
    stage: Mapped[str | None] = mapped_column(String(64))
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[DocStatus] = mapped_column(_enum(DocStatus), default=DocStatus.PENDING_UPLOAD)
    version: Mapped[int] = mapped_column(Integer, default=0)
    file_id: Mapped[int | None] = mapped_column(ForeignKey("file_objects.id"))
    uploader_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    review_remark: Mapped[str | None] = mapped_column(Text)
    secret_level: Mapped[SecretLevel] = mapped_column(_enum(SecretLevel), default=SecretLevel.INTERNAL)
    remark: Mapped[str | None] = mapped_column(Text)

    project: Mapped["Project | None"] = relationship(lazy="selectin")
    uploader: Mapped["User | None"] = relationship(lazy="selectin", foreign_keys=[uploader_id])
    reviewer: Mapped["User | None"] = relationship(lazy="selectin", foreign_keys=[reviewer_id])


# ---------------- 成本管理 ----------------
class Budget(TimestampMixin, Base):
    """项目预算科目。"""
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("project_id", "category", name="uq_budget_project_category"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)  # 成本科目
    budget_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    remark: Mapped[str | None] = mapped_column(String(255))


class Expense(TimestampMixin, Base):
    """支出登记（含分包付款）。"""
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    category: Mapped[str | None] = mapped_column(String(64))      # 对应预算科目
    type: Mapped[ExpenseType] = mapped_column(_enum(ExpenseType), default=ExpenseType.OTHER)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    payee: Mapped[str | None] = mapped_column(String(128))        # 供应商/分包商
    expense_date: Mapped[date | None] = mapped_column(Date)
    has_invoice: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否有票
    status: Mapped[ExpenseStatus] = mapped_column(_enum(ExpenseStatus), default=ExpenseStatus.REGISTERED)
    over_budget: Mapped[bool] = mapped_column(Boolean, default=False)
    applicant_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approve_remark: Mapped[str | None] = mapped_column(Text)
    remark: Mapped[str | None] = mapped_column(Text)

    applicant: Mapped["User | None"] = relationship(lazy="selectin", foreign_keys=[applicant_id])


# ---------------- 财税账本 ----------------
class FinanceRecord(TimestampMixin, Base):
    """收支流水（含发票登记与无票标记）。"""
    __tablename__ = "finance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    direction: Mapped[FinanceDirection] = mapped_column(_enum(FinanceDirection))
    category: Mapped[str | None] = mapped_column(String(64))       # 进度款/材料款/税费等
    amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    tax_rate: Mapped[float] = mapped_column(Numeric(6, 4), default=0)   # 税率，如 0.09
    tax_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    has_invoice: Mapped[bool] = mapped_column(Boolean, default=True)
    invoice_no: Mapped[str | None] = mapped_column(String(64))
    counterparty: Mapped[str | None] = mapped_column(String(128))  # 对方主体（开票/收票方）
    record_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[FinanceStatus] = mapped_column(_enum(FinanceStatus), default=FinanceStatus.POSTED)
    risk_tag: Mapped[str | None] = mapped_column(String(64))       # 风险标签
    remark: Mapped[str | None] = mapped_column(Text)


# ---------------- 回款清欠 ----------------
class Receivable(TimestampMixin, Base):
    """债权（应收/欠款）。"""
    __tablename__ = "receivables"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("client_units.id"))
    debt_type: Mapped[DebtType] = mapped_column(_enum(DebtType), default=DebtType.PROGRESS)
    contract_no: Mapped[str | None] = mapped_column(String(64))
    amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)          # 欠款金额
    received_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)  # 已回款
    due_date: Mapped[date | None] = mapped_column(Date)                        # 应收到期日
    stage: Mapped[str | None] = mapped_column(String(64))                      # 催收阶段
    status: Mapped[ReceivableStatus] = mapped_column(_enum(ReceivableStatus), default=ReceivableStatus.NORMAL)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    evidence_file_id: Mapped[int | None] = mapped_column(ForeignKey("file_objects.id"))  # 证据附件
    remark: Mapped[str | None] = mapped_column(Text)

    project: Mapped["Project | None"] = relationship(lazy="selectin")
    client: Mapped["ClientUnit | None"] = relationship(lazy="selectin")
    owner: Mapped["User | None"] = relationship(lazy="selectin")


class CollectionLog(Base):
    """催收/沟通日志。"""
    __tablename__ = "collection_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    receivable_id: Mapped[int] = mapped_column(ForeignKey("receivables.id", ondelete="CASCADE"), index=True)
    type: Mapped[CollectionLogType] = mapped_column(_enum(CollectionLogType), default=CollectionLogType.PHONE)
    content: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(String(255))
    amount: Mapped[float | None] = mapped_column(Numeric(18, 2))  # 回款登记时的金额
    operator_id: Mapped[int | None] = mapped_column(Integer)
    operator_name: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


# ---------------- 招投标 ----------------
class Tender(TimestampMixin, Base):
    """标讯 / 投标项目台账。"""
    __tablename__ = "tenders"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str | None] = mapped_column(String(128))          # 公告来源
    project_type: Mapped[str | None] = mapped_column(String(64))     # 项目类型
    region: Mapped[str | None] = mapped_column(String(64))           # 地域
    qualification_req: Mapped[str | None] = mapped_column(Text)      # 资质要求
    region_req: Mapped[str | None] = mapped_column(String(64))       # 地域要求
    registration_deadline: Mapped[date | None] = mapped_column(Date)  # 报名截止
    bid_open_time: Mapped[date | None] = mapped_column(Date)         # 开标时间
    deposit_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)  # 保证金
    deposit_due: Mapped[date | None] = mapped_column(Date)           # 保证金应退日
    deposit_returned: Mapped[bool] = mapped_column(Boolean, default=False)    # 保证金是否退回
    status: Mapped[TenderStatus] = mapped_column(_enum(TenderStatus), default=TenderStatus.PENDING_EVAL)
    eval_reason: Mapped[str | None] = mapped_column(Text)            # 准入评估结论
    fail_reason: Mapped[str | None] = mapped_column(String(255))     # 废标原因
    competitor_info: Mapped[str | None] = mapped_column(Text)        # 竞品信息
    win_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)  # 中标金额
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    secret_level: Mapped[SecretLevel] = mapped_column(_enum(SecretLevel), default=SecretLevel.INTERNAL)
    remark: Mapped[str | None] = mapped_column(Text)

    owner: Mapped["User | None"] = relationship(lazy="selectin")


# ---------------- 劳务法务 ----------------
class Worker(TimestampMixin, Base):
    """工人档案（实名/班组/工种/合同/工伤保险）。"""
    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    id_card: Mapped[str | None] = mapped_column(String(32))      # 身份证（脱敏存储建议）
    team: Mapped[str | None] = mapped_column(String(64))         # 班组
    craft: Mapped[str | None] = mapped_column(String(64))        # 工种
    entry_date: Mapped[date | None] = mapped_column(Date)        # 入场日期
    status: Mapped[WorkerStatus] = mapped_column(_enum(WorkerStatus), default=WorkerStatus.PENDING)
    contract_signed: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否签订劳动合同
    insurance_expiry: Mapped[date | None] = mapped_column(Date)  # 工伤保险到期（空=未参保）
    bank_account: Mapped[str | None] = mapped_column(String(64))  # 代发账户
    risk_tag: Mapped[str | None] = mapped_column(String(128))    # 风险标签（扫描生成）
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    remark: Mapped[str | None] = mapped_column(Text)

    project: Mapped["Project | None"] = relationship(lazy="selectin")


class PayrollRecord(Base):
    """工资发放记录。"""
    __tablename__ = "payroll_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String(16))             # 工资期间，如 2026-05
    amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否已发放
    pay_date: Mapped[date | None] = mapped_column(Date)
    bank_flow_no: Mapped[str | None] = mapped_column(String(64))  # 代发流水号
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


# ---------------- 第三方集成 ----------------
class IntegrationLog(Base):
    """第三方集成调用留痕（短信/电子签/OCR）。"""
    __tablename__ = "integration_logs"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    channel: Mapped[str] = mapped_column(String(16))     # sms / esign / ocr
    provider: Mapped[str] = mapped_column(String(32))    # mock / 真实厂商代号
    action: Mapped[str] = mapped_column(String(32))      # send / initiate / recognize
    target: Mapped[str | None] = mapped_column(String(255))  # 手机号/文件名/签署方
    status: Mapped[str] = mapped_column(String(16), default="success")  # success / failed
    request_summary: Mapped[str | None] = mapped_column(Text)
    response_summary: Mapped[str | None] = mapped_column(Text)
    operator_id: Mapped[int | None] = mapped_column(Integer)
    operator_name: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)


# ---------------- 用户反馈 ----------------
class Feedback(TimestampMixin, Base):
    """用户反馈/建议。"""
    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    page_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[FeedbackStatus] = mapped_column(_enum(FeedbackStatus), default=FeedbackStatus.PENDING)
