export const PROJECT_STATUS: Record<string, { label: string; color: string }> = {
  preparing: { label: '筹备', color: 'default' },
  ongoing: { label: '在建', color: 'processing' },
  suspended: { label: '停工', color: 'warning' },
  completed: { label: '竣工', color: 'success' },
  settling: { label: '结算中', color: 'cyan' },
  collecting: { label: '清欠中', color: 'volcano' },
  archived: { label: '归档', color: 'default' },
}

export const SECRET_LEVEL: Record<string, { label: string; color: string }> = {
  public: { label: '公开', color: 'default' },
  internal: { label: '内部', color: 'blue' },
  sensitive: { label: '敏感', color: 'orange' },
  classified: { label: '涉密', color: 'red' },
}

export const ALERT_LEVEL: Record<string, { label: string; color: string }> = {
  low: { label: '一般', color: 'default' },
  medium: { label: '关注', color: 'blue' },
  high: { label: '预警', color: 'orange' },
  critical: { label: '高风险', color: 'red' },
}

export const ALERT_STATUS: Record<string, { label: string; color: string }> = {
  pending: { label: '待处理', color: 'gold' },
  processing: { label: '处理中', color: 'processing' },
  closed: { label: '已关闭', color: 'success' },
  overdue: { label: '已逾期', color: 'error' },
  escalated: { label: '已升级', color: 'volcano' },
}

export const ALERT_SOURCE: Record<string, string> = {
  qualification: '资质',
  document: '资料',
  cost: '成本',
  finance: '财税',
  receivable: '回款',
  secret: '涉密',
  bid: '招投标',
  labor: '劳务',
}

export const FILE_STATUS: Record<string, { label: string; color: string }> = {
  active: { label: '有效', color: 'success' },
  replaced: { label: '已替换', color: 'default' },
  archived: { label: '已归档', color: 'blue' },
  deleted: { label: '已删除', color: 'error' },
  restricted: { label: '受限', color: 'orange' },
}

export const fmtMoney = (v: string | number) => {
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (isNaN(n)) return '-'
  return (n / 10000).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) + ' 万'
}

export const QUAL_STATUS: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'default' },
  pending_verify: { label: '待核验', color: 'gold' },
  valid: { label: '有效', color: 'success' },
  expiring: { label: '即将到期', color: 'orange' },
  expired: { label: '已过期', color: 'red' },
  rectifying: { label: '整改中', color: 'volcano' },
  disabled: { label: '停用', color: 'default' },
}

export const VERIFY_STATUS: Record<string, { label: string; color: string }> = {
  unverified: { label: '未核验', color: 'default' },
  verified: { label: '已核验', color: 'success' },
  failed: { label: '核验未通过', color: 'error' },
}

export const DOC_STATUS: Record<string, { label: string; color: string }> = {
  pending_upload: { label: '待上传', color: 'default' },
  pending_review: { label: '待审核', color: 'processing' },
  returned: { label: '需退回', color: 'volcano' },
  approved: { label: '已通过', color: 'success' },
  missing: { label: '缺项', color: 'red' },
  archived: { label: '已组卷', color: 'blue' },
}

export const EXPENSE_TYPE: Record<string, string> = {
  material: '材料',
  labor: '人工',
  machine: '机械',
  subcontract: '分包',
  other: '其他',
}

export const EXPENSE_STATUS: Record<string, { label: string; color: string }> = {
  registered: { label: '已登记', color: 'default' },
  pending_approval: { label: '待审批', color: 'gold' },
  paid: { label: '已付款', color: 'success' },
  rejected: { label: '已驳回', color: 'error' },
}

export const FINANCE_STATUS: Record<string, { label: string; color: string }> = {
  pending: { label: '待入账', color: 'default' },
  posted: { label: '已入账', color: 'success' },
  pending_invoice: { label: '待补票', color: 'orange' },
  abnormal: { label: '异常', color: 'red' },
  archived: { label: '已归档', color: 'blue' },
}

export const DEBT_TYPE: Record<string, string> = {
  progress: '进度款',
  final: '竣工尾款',
  warranty: '质保金',
  advance: '垫资款',
  other: '其他',
}

export const RECEIVABLE_STATUS: Record<string, { label: string; color: string }> = {
  normal: { label: '正常回款', color: 'success' },
  overdue: { label: '逾期', color: 'orange' },
  stagnant: { label: '呆滞', color: 'volcano' },
  bad_debt_risk: { label: '坏账风险', color: 'red' },
  legal_process: { label: '诉讼处理中', color: 'magenta' },
  partial: { label: '部分回款', color: 'cyan' },
  settled: { label: '已结清', color: 'green' },
  written_off: { label: '已核销', color: 'default' },
}

export const COLLECTION_LOG_TYPE: Record<string, string> = {
  phone: '电话',
  visit: '上门',
  letter: '函件',
  reconcile: '对账',
  payment: '回款',
  other: '其他',
}

export const CREDIT_COLOR: Record<string, string> = {
  A: 'green', B: 'blue', C: 'orange', D: 'red',
}

export const TENDER_STATUS: Record<string, { label: string; color: string }> = {
  pending_eval: { label: '待评估', color: 'default' },
  can_bid: { label: '可投', color: 'green' },
  cannot_bid: { label: '不可投', color: 'red' },
  registering: { label: '报名中', color: 'blue' },
  preparing: { label: '标书制作中', color: 'cyan' },
  bidded: { label: '已投标', color: 'processing' },
  won: { label: '已中标', color: 'success' },
  lost: { label: '未中标', color: 'volcano' },
  failed: { label: '废标', color: 'error' },
  archived: { label: '归档', color: 'default' },
}

export const WORKER_STATUS: Record<string, { label: string; color: string }> = {
  pending: { label: '待入场', color: 'default' },
  onsite: { label: '在场', color: 'processing' },
  left: { label: '离场', color: 'default' },
}
