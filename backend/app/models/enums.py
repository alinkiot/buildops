"""业务枚举定义。"""
from __future__ import annotations

import enum


class SecretLevel(str, enum.Enum):
    """数据密级：普通/内部/敏感/涉密"""
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    CLASSIFIED = "classified"


class CommonStatus(str, enum.Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class DataScope(str, enum.Enum):
    """角色数据范围"""
    ALL = "all"            # 全部数据
    DEPT = "dept"          # 本部门
    DEPT_AND_SUB = "dept_and_sub"  # 本部门及下级
    SELF = "self"          # 仅本人
    PROJECT = "project"    # 仅授权项目


class ProjectStatus(str, enum.Enum):
    PREPARING = "preparing"      # 筹备
    ONGOING = "ongoing"          # 在建
    SUSPENDED = "suspended"      # 停工
    COMPLETED = "completed"      # 竣工
    SETTLING = "settling"        # 结算中
    COLLECTING = "collecting"    # 清欠中
    ARCHIVED = "archived"        # 归档


class FileStatus(str, enum.Enum):
    ACTIVE = "active"            # 有效
    REPLACED = "replaced"        # 已替换
    ARCHIVED = "archived"        # 已归档
    DELETED = "deleted"          # 已删除
    RESTRICTED = "restricted"    # 受限访问


class AlertLevel(str, enum.Enum):
    LOW = "low"            # 一般
    MEDIUM = "medium"      # 关注
    HIGH = "high"          # 预警
    CRITICAL = "critical"  # 高风险


class AlertStatus(str, enum.Enum):
    PENDING = "pending"        # 待处理
    PROCESSING = "processing"  # 处理中
    CLOSED = "closed"          # 已关闭
    OVERDUE = "overdue"        # 已逾期
    ESCALATED = "escalated"    # 已升级


class AlertSource(str, enum.Enum):
    QUALIFICATION = "qualification"  # 资质
    DOCUMENT = "document"            # 资料
    COST = "cost"                    # 成本
    FINANCE = "finance"              # 财税
    RECEIVABLE = "receivable"        # 回款
    SECRET = "secret"                # 涉密
    BID = "bid"                      # 招投标
    LABOR = "labor"                  # 劳务法务


class QualificationStatus(str, enum.Enum):
    DRAFT = "draft"              # 草稿
    PENDING_VERIFY = "pending_verify"  # 待核验
    VALID = "valid"             # 有效
    EXPIRING = "expiring"       # 即将到期
    EXPIRED = "expired"         # 已过期
    RECTIFYING = "rectifying"   # 整改中
    DISABLED = "disabled"       # 停用


class VerifyStatus(str, enum.Enum):
    UNVERIFIED = "unverified"   # 未核验
    VERIFIED = "verified"       # 已核验
    FAILED = "failed"           # 核验未通过


class DocStatus(str, enum.Enum):
    PENDING_UPLOAD = "pending_upload"  # 待上传
    PENDING_REVIEW = "pending_review"  # 待审核
    RETURNED = "returned"              # 需退回
    APPROVED = "approved"              # 已通过
    MISSING = "missing"                # 缺项（逾期未交）
    ARCHIVED = "archived"              # 已组卷归档


class ExpenseType(str, enum.Enum):
    MATERIAL = "material"        # 材料
    LABOR = "labor"             # 人工
    MACHINE = "machine"         # 机械台班
    SUBCONTRACT = "subcontract" # 分包
    OTHER = "other"             # 其他


class ExpenseStatus(str, enum.Enum):
    REGISTERED = "registered"          # 已登记
    PENDING_APPROVAL = "pending_approval"  # 待审批（超预算）
    PAID = "paid"                      # 已付款
    REJECTED = "rejected"              # 已驳回


class FinanceDirection(str, enum.Enum):
    INCOME = "income"    # 收入
    EXPENSE = "expense"  # 支出


class FinanceStatus(str, enum.Enum):
    PENDING = "pending"                # 待入账
    POSTED = "posted"                  # 已入账
    PENDING_INVOICE = "pending_invoice"  # 待补票
    ABNORMAL = "abnormal"              # 异常
    ARCHIVED = "archived"              # 已归档


class DebtType(str, enum.Enum):
    PROGRESS = "progress"    # 进度款
    FINAL = "final"          # 竣工尾款
    WARRANTY = "warranty"    # 质保金
    ADVANCE = "advance"      # 垫资款
    OTHER = "other"          # 其他


class ReceivableStatus(str, enum.Enum):
    NORMAL = "normal"              # 正常回款
    OVERDUE = "overdue"            # 逾期
    STAGNANT = "stagnant"          # 呆滞
    BAD_DEBT_RISK = "bad_debt_risk"  # 坏账风险
    LEGAL_PROCESS = "legal_process"  # 非诉/诉讼处理中
    PARTIAL = "partial"            # 部分回款
    SETTLED = "settled"            # 已结清
    WRITTEN_OFF = "written_off"    # 已核销


class CollectionLogType(str, enum.Enum):
    PHONE = "phone"          # 电话催收
    VISIT = "visit"          # 上门催收
    LETTER = "letter"        # 函件/文书
    RECONCILE = "reconcile"  # 对账
    PAYMENT = "payment"      # 回款登记
    OTHER = "other"


class TenderStatus(str, enum.Enum):
    PENDING_EVAL = "pending_eval"    # 待评估
    CAN_BID = "can_bid"              # 可投
    CANNOT_BID = "cannot_bid"        # 不可投
    REGISTERING = "registering"      # 报名中
    PREPARING = "preparing"          # 标书制作中
    BIDDED = "bidded"                # 已投标
    WON = "won"                      # 已中标
    LOST = "lost"                    # 未中标
    FAILED = "failed"                # 废标
    ARCHIVED = "archived"            # 归档


class WorkerStatus(str, enum.Enum):
    PENDING = "pending"  # 待入场
    ONSITE = "onsite"    # 在场
    LEFT = "left"        # 离场


class FeedbackStatus(str, enum.Enum):
    PENDING = "pending"        # 待确认
    PROCESSING = "processing"  # 处理中
    IGNORED = "ignored"        # 不处理
    RESOLVED = "resolved"      # 已解决
