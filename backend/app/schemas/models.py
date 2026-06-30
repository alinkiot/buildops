"""请求/响应数据模型（Pydantic v2）。"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import (
    AlertLevel,
    AlertSource,
    AlertStatus,
    CommonStatus,
    DataScope,
    FileStatus,
    ProjectStatus,
    SecretLevel,
)


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------- 认证 ----------------
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PermissionOut(ORMBase):
    code: str
    name: str
    type: str
    parent_code: str | None = None
    path: str | None = None
    sort: int = 0


class RoleBrief(ORMBase):
    id: int
    code: str
    name: str
    data_scope: DataScope


class UserProjectAuth(BaseModel):
    project_ids: list[int] = []


class CurrentUser(ORMBase):
    id: int
    tenant_id: int
    username: str
    name: str
    phone: str | None = None
    email: str | None = None
    department_id: int | None = None
    is_superadmin: bool
    roles: list[RoleBrief] = []
    permissions: list[str] = []


# ---------------- 部门 ----------------
class DepartmentIn(BaseModel):
    name: str
    parent_id: int | None = None
    sort: int = 0


class DepartmentOut(ORMBase):
    id: int
    name: str
    parent_id: int | None = None
    sort: int = 0


# ---------------- 用户 ----------------
class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=64)
    name: str
    phone: str | None = None
    email: EmailStr | None = None
    department_id: int | None = None
    role_ids: list[int] = []


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    department_id: int | None = None
    status: CommonStatus | None = None
    role_ids: list[int] | None = None


class UserOut(ORMBase):
    id: int
    username: str
    name: str
    phone: str | None = None
    email: str | None = None
    department_id: int | None = None
    status: CommonStatus
    is_superadmin: bool
    last_login_at: datetime | None = None
    created_at: datetime
    roles: list[RoleBrief] = []


# ---------------- 角色 ----------------
class RoleCreate(BaseModel):
    code: str
    name: str
    data_scope: DataScope = DataScope.SELF
    remark: str | None = None
    permission_codes: list[str] = []


class RoleUpdate(BaseModel):
    name: str | None = None
    data_scope: DataScope | None = None
    remark: str | None = None
    status: CommonStatus | None = None
    permission_codes: list[str] | None = None


class RoleOut(ORMBase):
    id: int
    code: str
    name: str
    data_scope: DataScope
    remark: str | None = None
    status: CommonStatus
    created_at: datetime
    permissions: list[PermissionOut] = []


# ---------------- 甲方 ----------------
class ClientIn(BaseModel):
    name: str
    contact: str | None = None
    phone: str | None = None
    credit_rating: str | None = None
    remark: str | None = None


class ClientOut(ORMBase):
    id: int
    name: str
    contact: str | None = None
    phone: str | None = None
    credit_rating: str | None = None
    remark: str | None = None


# ---------------- 项目 ----------------
class ProjectCreate(BaseModel):
    code: str
    name: str
    type: str | None = None
    region: str | None = None
    owner_id: int | None = None
    client_id: int | None = None
    contract_amount: Decimal = Decimal("0")
    start_date: date | None = None
    plan_end_date: date | None = None
    status: ProjectStatus = ProjectStatus.PREPARING
    secret_level: SecretLevel = SecretLevel.INTERNAL
    remark: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    region: str | None = None
    owner_id: int | None = None
    client_id: int | None = None
    contract_amount: Decimal | None = None
    received_amount: Decimal | None = None
    cost_amount: Decimal | None = None
    start_date: date | None = None
    plan_end_date: date | None = None
    status: ProjectStatus | None = None
    secret_level: SecretLevel | None = None
    remark: str | None = None


class UserBrief(ORMBase):
    id: int
    name: str


class ProjectOut(ORMBase):
    id: int
    code: str
    name: str
    type: str | None = None
    region: str | None = None
    owner_id: int | None = None
    owner: UserBrief | None = None
    client_id: int | None = None
    client: ClientOut | None = None
    contract_amount: Decimal
    received_amount: Decimal
    cost_amount: Decimal
    start_date: date | None = None
    plan_end_date: date | None = None
    status: ProjectStatus
    secret_level: SecretLevel
    remark: str | None = None
    created_at: datetime


# ---------------- 文件 ----------------
class FileOut(ORMBase):
    id: int
    name: str
    business_type: str | None = None
    project_id: int | None = None
    version: int
    size: int
    content_type: str | None = None
    secret_level: SecretLevel
    uploader_id: int | None = None
    download_count: int
    status: FileStatus
    created_at: datetime


class FileUpdate(BaseModel):
    name: str | None = None
    business_type: str | None = None
    secret_level: SecretLevel | None = None
    status: FileStatus | None = None


# ---------------- 预警 ----------------
class AlertRuleIn(BaseModel):
    code: str
    name: str
    source: AlertSource
    level: AlertLevel = AlertLevel.MEDIUM
    enabled: bool = True
    remark: str | None = None


class AlertRuleOut(ORMBase):
    id: int
    code: str
    name: str
    source: AlertSource
    level: AlertLevel
    enabled: bool
    remark: str | None = None


class AlertCreate(BaseModel):
    title: str
    source: AlertSource
    project_id: int | None = None
    rule_id: int | None = None
    level: AlertLevel = AlertLevel.MEDIUM
    owner_id: int | None = None
    due_date: date | None = None


class AlertHandle(BaseModel):
    status: AlertStatus
    handle_remark: str | None = None


class AlertOut(ORMBase):
    id: int
    title: str
    source: AlertSource
    project_id: int | None = None
    project: "ProjectBrief | None" = None
    rule_id: int | None = None
    level: AlertLevel
    owner_id: int | None = None
    owner: UserBrief | None = None
    due_date: date | None = None
    status: AlertStatus
    handle_remark: str | None = None
    created_at: datetime
    closed_at: datetime | None = None


class ProjectBrief(ORMBase):
    id: int
    code: str
    name: str


AlertOut.model_rebuild()


# ---------------- 驾驶舱 ----------------
class DashboardOverview(BaseModel):
    project_count: int
    ongoing_count: int
    contract_amount: Decimal
    received_amount: Decimal
    cost_amount: Decimal
    profit_amount: Decimal
    receivable_amount: Decimal
    alert_count: int
    pending_alert_count: int


class NameValue(BaseModel):
    name: str
    value: Decimal | int


class DashboardData(BaseModel):
    overview: DashboardOverview
    project_profit_rank: list[dict]
    alert_by_source: list[NameValue]
    alert_by_level: list[NameValue]
    project_by_status: list[NameValue]
    modules: "ModuleOverview | None" = None


# ---------------- 资质合规 ----------------
from app.models.enums import QualificationStatus, VerifyStatus  # noqa: E402


class QualificationCreate(BaseModel):
    name: str
    type: str | None = None
    level: str | None = None
    cert_no: str | None = None
    issuing_authority: str | None = None
    scope: str | None = None
    region_limit: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    annual_review_date: date | None = None
    status: QualificationStatus = QualificationStatus.VALID
    secret_level: SecretLevel = SecretLevel.INTERNAL
    owner_id: int | None = None
    file_id: int | None = None
    remark: str | None = None


class QualificationUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    level: str | None = None
    cert_no: str | None = None
    issuing_authority: str | None = None
    scope: str | None = None
    region_limit: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    annual_review_date: date | None = None
    status: QualificationStatus | None = None
    secret_level: SecretLevel | None = None
    owner_id: int | None = None
    file_id: int | None = None
    remark: str | None = None


class QualificationOut(ORMBase):
    id: int
    name: str
    type: str | None = None
    level: str | None = None
    cert_no: str | None = None
    issuing_authority: str | None = None
    scope: str | None = None
    region_limit: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    annual_review_date: date | None = None
    verify_status: VerifyStatus
    status: QualificationStatus
    secret_level: SecretLevel
    owner_id: int | None = None
    owner: UserBrief | None = None
    file_id: int | None = None
    remark: str | None = None
    created_at: datetime
    days_to_expire: int | None = None  # 计算字段：距到期天数


class VerifyRecordCreate(BaseModel):
    result: VerifyStatus
    method: str | None = None
    remark: str | None = None


class VerifyRecordOut(ORMBase):
    id: int
    qualification_id: int
    result: VerifyStatus
    method: str | None = None
    remark: str | None = None
    operator_name: str | None = None
    created_at: datetime


class ScanResult(BaseModel):
    scanned: int
    expiring: int
    expired: int
    alerts_created: int


# ---------------- 工程资料 ----------------
from app.models.enums import DocStatus  # noqa: E402


class DocTemplateIn(BaseModel):
    name: str
    category: str | None = None
    specialty: str | None = None
    stage: str | None = None
    required: bool = True
    sort: int = 0
    remark: str | None = None


class DocTemplateOut(ORMBase):
    id: int
    name: str
    category: str | None = None
    specialty: str | None = None
    stage: str | None = None
    required: bool
    sort: int
    remark: str | None = None


class DocItemCreate(BaseModel):
    project_id: int
    name: str
    category: str | None = None
    specialty: str | None = None
    stage: str | None = None
    required: bool = True
    due_date: date | None = None
    secret_level: SecretLevel = SecretLevel.INTERNAL
    remark: str | None = None


class DocItemUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    specialty: str | None = None
    stage: str | None = None
    required: bool | None = None
    due_date: date | None = None
    secret_level: SecretLevel | None = None
    remark: str | None = None


class DocReview(BaseModel):
    approved: bool
    review_remark: str | None = None


class ApplyTemplateRequest(BaseModel):
    project_id: int
    template_ids: list[int] = []  # 为空表示应用全部模板
    default_due_date: date | None = None


class DocItemOut(ORMBase):
    id: int
    project_id: int
    name: str
    category: str | None = None
    specialty: str | None = None
    stage: str | None = None
    required: bool
    due_date: date | None = None
    status: DocStatus
    version: int
    file_id: int | None = None
    uploader_id: int | None = None
    uploader: UserBrief | None = None
    reviewer_id: int | None = None
    reviewer: UserBrief | None = None
    review_remark: str | None = None
    secret_level: SecretLevel
    remark: str | None = None
    created_at: datetime
    overdue: bool = False  # 计算字段：是否逾期未通过


class CompletenessOut(BaseModel):
    project_id: int
    total: int
    required_total: int
    approved: int
    pending_upload: int
    pending_review: int
    returned: int
    missing: int
    completeness: float  # 已通过 / 应交（必需项）百分比


class DocScanResult(BaseModel):
    scanned: int
    missing: int
    alerts_created: int


class ArchiveResult(BaseModel):
    archived: int
    manifest: list[dict]


# ---------------- 成本管理 ----------------
from app.models.enums import ExpenseStatus, ExpenseType  # noqa: E402


class BudgetIn(BaseModel):
    project_id: int
    category: str
    budget_amount: Decimal = Decimal("0")
    remark: str | None = None


class BudgetUpdate(BaseModel):
    category: str | None = None
    budget_amount: Decimal | None = None
    remark: str | None = None


class BudgetOut(ORMBase):
    id: int
    project_id: int
    category: str
    budget_amount: Decimal
    remark: str | None = None
    created_at: datetime


class ExpenseCreate(BaseModel):
    project_id: int
    category: str | None = None
    type: ExpenseType = ExpenseType.OTHER
    amount: Decimal
    payee: str | None = None
    expense_date: date | None = None
    has_invoice: bool = True
    remark: str | None = None


class ExpenseApprove(BaseModel):
    approved: bool
    approve_remark: str | None = None


class ExpenseOut(ORMBase):
    id: int
    project_id: int
    category: str | None = None
    type: ExpenseType
    amount: Decimal
    payee: str | None = None
    expense_date: date | None = None
    has_invoice: bool
    status: ExpenseStatus
    over_budget: bool
    applicant_id: int | None = None
    applicant: UserBrief | None = None
    approver_id: int | None = None
    approve_remark: str | None = None
    remark: str | None = None
    created_at: datetime


class BudgetDeviation(BaseModel):
    category: str
    budget_amount: Decimal
    actual_amount: Decimal
    remaining: Decimal
    deviation_rate: float  # (实际-预算)/预算 百分比
    over_budget: bool


class CostSummary(BaseModel):
    project_id: int
    total_budget: Decimal
    total_actual: Decimal
    total_remaining: Decimal
    deviation_rate: float
    pending_approval: int
    no_invoice_amount: Decimal
    deviations: list[BudgetDeviation]


# ---------------- 财税账本 ----------------
from app.models.enums import FinanceDirection, FinanceStatus  # noqa: E402


class FinanceRecordCreate(BaseModel):
    project_id: int
    direction: FinanceDirection
    category: str | None = None
    amount: Decimal
    tax_rate: Decimal = Decimal("0")
    tax_amount: Decimal | None = None  # 不传则按 amount*tax_rate 估算
    has_invoice: bool = True
    invoice_no: str | None = None
    counterparty: str | None = None
    record_date: date | None = None
    status: FinanceStatus = FinanceStatus.POSTED
    remark: str | None = None


class FinanceRecordUpdate(BaseModel):
    category: str | None = None
    amount: Decimal | None = None
    tax_rate: Decimal | None = None
    tax_amount: Decimal | None = None
    has_invoice: bool | None = None
    invoice_no: str | None = None
    counterparty: str | None = None
    record_date: date | None = None
    status: FinanceStatus | None = None
    remark: str | None = None


class FinanceRecordOut(ORMBase):
    id: int
    project_id: int
    direction: FinanceDirection
    category: str | None = None
    amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    has_invoice: bool
    invoice_no: str | None = None
    counterparty: str | None = None
    record_date: date | None = None
    status: FinanceStatus
    risk_tag: str | None = None
    remark: str | None = None
    created_at: datetime


class ProfitStatement(BaseModel):
    project_id: int
    total_income: Decimal
    total_expense: Decimal
    total_tax: Decimal
    gross_profit: Decimal      # 收入 - 支出
    net_profit: Decimal        # 收入 - 支出 - 税费
    net_margin: float          # 净利率 %
    invoiced_income: Decimal
    no_invoice_expense: Decimal
    no_invoice_ratio: float    # 无票支出占比 %


class FinanceScanResult(BaseModel):
    scanned: int
    no_invoice_expense: Decimal
    total_expense: Decimal
    no_invoice_ratio: float
    flagged: int
    alerts_created: int


# ---------------- 回款清欠 ----------------
from app.models.enums import CollectionLogType, DebtType, ReceivableStatus  # noqa: E402


class ReceivableCreate(BaseModel):
    project_id: int | None = None
    client_id: int | None = None
    debt_type: DebtType = DebtType.PROGRESS
    contract_no: str | None = None
    amount: Decimal
    received_amount: Decimal = Decimal("0")
    due_date: date | None = None
    stage: str | None = None
    status: ReceivableStatus = ReceivableStatus.NORMAL
    owner_id: int | None = None
    evidence_file_id: int | None = None
    remark: str | None = None


class ReceivableUpdate(BaseModel):
    client_id: int | None = None
    debt_type: DebtType | None = None
    contract_no: str | None = None
    amount: Decimal | None = None
    due_date: date | None = None
    stage: str | None = None
    status: ReceivableStatus | None = None
    owner_id: int | None = None
    evidence_file_id: int | None = None
    remark: str | None = None


class ReceivableOut(ORMBase):
    id: int
    project_id: int | None = None
    project: "ProjectBrief | None" = None
    client_id: int | None = None
    client: ClientOut | None = None
    debt_type: DebtType
    contract_no: str | None = None
    amount: Decimal
    received_amount: Decimal
    outstanding: Decimal = Decimal("0")  # 未回款 = amount - received
    due_date: date | None = None
    overdue_days: int = 0                # 逾期天数（计算字段）
    stage: str | None = None
    status: ReceivableStatus
    owner_id: int | None = None
    owner: UserBrief | None = None
    evidence_file_id: int | None = None
    remark: str | None = None
    created_at: datetime


class CollectionLogIn(BaseModel):
    type: CollectionLogType = CollectionLogType.PHONE
    content: str | None = None
    result: str | None = None


class CollectionLogOut(ORMBase):
    id: int
    receivable_id: int
    type: CollectionLogType
    content: str | None = None
    result: str | None = None
    amount: Decimal | None = None
    operator_name: str | None = None
    created_at: datetime


class PaymentIn(BaseModel):
    amount: Decimal
    record_date: date | None = None
    remark: str | None = None
    sync_finance: bool = True  # 同步生成财税收入流水


class ReceivableScanResult(BaseModel):
    scanned: int
    overdue: int
    stagnant: int
    bad_debt_risk: int
    alerts_created: int


class ReceivableTier(BaseModel):
    name: str
    count: int
    outstanding: Decimal


class ClientCredit(BaseModel):
    client_id: int | None = None
    client_name: str
    total_amount: Decimal
    received_amount: Decimal
    outstanding: Decimal
    overdue_outstanding: Decimal
    credit_score: int          # 0-100
    credit_level: str          # A/B/C/D


class ReceivableSummary(BaseModel):
    total_amount: Decimal
    total_received: Decimal
    total_outstanding: Decimal
    overdue_outstanding: Decimal
    tiers: list[ReceivableTier]
    clients: list[ClientCredit]


ReceivableOut.model_rebuild()


# ---------------- 驾驶舱模块经营概览 ----------------
class QualHealth(BaseModel):
    total: int
    valid: int
    expiring: int
    expired: int
    health_score: int  # 资质健康度评分 0-100


class DocHealth(BaseModel):
    required_total: int
    approved: int
    missing: int
    completeness: float  # 资料完整度 %


class CostHealth(BaseModel):
    total_budget: Decimal
    total_actual: Decimal
    deviation_rate: float
    over_budget_projects: int
    pending_approval: int


class FinanceHealth(BaseModel):
    total_income: Decimal
    total_expense: Decimal
    total_tax: Decimal
    net_profit: Decimal
    no_invoice_ratio: float


class ReceivableHealth(BaseModel):
    total_outstanding: Decimal
    overdue_outstanding: Decimal
    overdue: int
    stagnant: int
    bad_debt_risk: int
    worst_client: str | None = None
    worst_client_level: str | None = None


class BidHealth(BaseModel):
    total: int
    bidded: int
    won: int
    win_rate: float
    deposit_outstanding: Decimal
    deposit_overdue: int


class LaborHealth(BaseModel):
    total: int
    onsite: int
    contract_missing: int
    insurance_missing: int
    risk_workers: int
    unpaid_amount: Decimal


class ModuleOverview(BaseModel):
    qualification: QualHealth
    document: DocHealth
    cost: CostHealth
    finance: FinanceHealth
    receivable: ReceivableHealth
    bid: BidHealth
    labor: LaborHealth


DashboardData.model_rebuild()


# ---------------- 招投标 ----------------
from app.models.enums import TenderStatus  # noqa: E402


class TenderCreate(BaseModel):
    name: str
    source: str | None = None
    project_type: str | None = None
    region: str | None = None
    qualification_req: str | None = None
    region_req: str | None = None
    registration_deadline: date | None = None
    bid_open_time: date | None = None
    deposit_amount: Decimal = Decimal("0")
    deposit_due: date | None = None
    status: TenderStatus = TenderStatus.PENDING_EVAL
    competitor_info: str | None = None
    owner_id: int | None = None
    secret_level: SecretLevel = SecretLevel.INTERNAL
    remark: str | None = None


class TenderUpdate(BaseModel):
    name: str | None = None
    source: str | None = None
    project_type: str | None = None
    region: str | None = None
    qualification_req: str | None = None
    region_req: str | None = None
    registration_deadline: date | None = None
    bid_open_time: date | None = None
    deposit_amount: Decimal | None = None
    deposit_due: date | None = None
    deposit_returned: bool | None = None
    status: TenderStatus | None = None
    fail_reason: str | None = None
    competitor_info: str | None = None
    win_amount: Decimal | None = None
    owner_id: int | None = None
    secret_level: SecretLevel | None = None
    remark: str | None = None


class TenderOut(ORMBase):
    id: int
    name: str
    source: str | None = None
    project_type: str | None = None
    region: str | None = None
    qualification_req: str | None = None
    region_req: str | None = None
    registration_deadline: date | None = None
    bid_open_time: date | None = None
    deposit_amount: Decimal
    deposit_due: date | None = None
    deposit_returned: bool
    status: TenderStatus
    eval_reason: str | None = None
    fail_reason: str | None = None
    competitor_info: str | None = None
    win_amount: Decimal
    owner_id: int | None = None
    owner: UserBrief | None = None
    secret_level: SecretLevel
    remark: str | None = None
    created_at: datetime


class TenderEvalResult(BaseModel):
    can_bid: bool
    reasons: list[str]
    status: TenderStatus


class TenderBoard(BaseModel):
    total: int
    by_status: list[NameValue]
    bidded: int           # 有效投标数（已投标+已中标+未中标）
    won: int
    win_rate: float       # 中标率 %
    deposit_outstanding: Decimal  # 未退保证金合计
    deposit_overdue: int  # 保证金逾期未退笔数


class DepositScanResult(BaseModel):
    scanned: int
    overdue: int
    alerts_created: int


# ---------------- 劳务法务 ----------------
from app.models.enums import WorkerStatus  # noqa: E402


class WorkerCreate(BaseModel):
    project_id: int | None = None
    name: str
    id_card: str | None = None
    team: str | None = None
    craft: str | None = None
    entry_date: date | None = None
    status: WorkerStatus = WorkerStatus.PENDING
    contract_signed: bool = False
    insurance_expiry: date | None = None
    bank_account: str | None = None
    owner_id: int | None = None
    remark: str | None = None


class WorkerUpdate(BaseModel):
    project_id: int | None = None
    name: str | None = None
    id_card: str | None = None
    team: str | None = None
    craft: str | None = None
    entry_date: date | None = None
    status: WorkerStatus | None = None
    contract_signed: bool | None = None
    insurance_expiry: date | None = None
    bank_account: str | None = None
    owner_id: int | None = None
    remark: str | None = None


class WorkerOut(ORMBase):
    id: int
    project_id: int | None = None
    project: "ProjectBrief | None" = None
    name: str
    id_card: str | None = None
    team: str | None = None
    craft: str | None = None
    entry_date: date | None = None
    status: WorkerStatus
    contract_signed: bool
    insurance_expiry: date | None = None
    bank_account: str | None = None
    risk_tag: str | None = None
    owner_id: int | None = None
    remark: str | None = None
    created_at: datetime


class PayrollCreate(BaseModel):
    period: str
    amount: Decimal
    paid: bool = False
    pay_date: date | None = None
    bank_flow_no: str | None = None
    remark: str | None = None


class PayrollOut(ORMBase):
    id: int
    worker_id: int
    period: str
    amount: Decimal
    paid: bool
    pay_date: date | None = None
    bank_flow_no: str | None = None
    remark: str | None = None
    created_at: datetime


class LaborScanResult(BaseModel):
    scanned: int
    contract_missing: int
    insurance_missing: int
    flagged: int
    alerts_created: int


class LaborSummary(BaseModel):
    total: int
    onsite: int
    contract_missing: int
    insurance_missing: int
    risk_workers: int
    unpaid_amount: Decimal
    by_team: list[NameValue]


WorkerOut.model_rebuild()


# ---------------- 第三方集成 ----------------
class SmsSendIn(BaseModel):
    to: str
    content: str


class ESignInitiateIn(BaseModel):
    doc_name: str
    signers: list[str] = []


class OcrRecognizeIn(BaseModel):
    filename: str
    doc_type: str = "invoice"  # invoice/contract/certificate/id_card


class IntegrationLogOut(ORMBase):
    id: int
    channel: str
    provider: str
    action: str
    target: str | None = None
    status: str
    request_summary: str | None = None
    response_summary: str | None = None
    operator_name: str | None = None
    created_at: datetime


class IntegrationProviders(BaseModel):
    sms: str
    esign: str
    ocr: str
