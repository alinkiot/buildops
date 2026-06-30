export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface PageResult<T> {
  items: T[]
  page: number
  page_size: number
  total: number
}

export interface RoleBrief {
  id: number
  code: string
  name: string
  data_scope: string
}

export interface CurrentUser {
  id: number
  tenant_id: number
  username: string
  name: string
  phone?: string
  email?: string
  department_id?: number
  is_superadmin: boolean
  roles: RoleBrief[]
  permissions: string[]
}

export interface Project {
  id: number
  code: string
  name: string
  type?: string
  region?: string
  owner_id?: number
  owner?: { id: number; name: string }
  client_id?: number
  client?: { id: number; name: string }
  contract_amount: string
  received_amount: string
  cost_amount: string
  start_date?: string
  plan_end_date?: string
  status: string
  secret_level: string
  remark?: string
  created_at: string
}

export interface FileObject {
  id: number
  name: string
  business_type?: string
  project_id?: number
  version: number
  size: number
  content_type?: string
  secret_level: string
  uploader_id?: number
  download_count: number
  status: string
  created_at: string
}

export interface Alert {
  id: number
  title: string
  source: string
  project_id?: number
  project?: { id: number; code: string; name: string }
  level: string
  owner_id?: number
  owner?: { id: number; name: string }
  due_date?: string
  status: string
  handle_remark?: string
  created_at: string
  closed_at?: string
}

export interface AlertRule {
  id: number
  code: string
  name: string
  source: string
  level: string
  enabled: boolean
  remark?: string
}

export interface UserRow {
  id: number
  username: string
  name: string
  phone?: string
  email?: string
  status: string
  is_superadmin: boolean
  last_login_at?: string
  created_at: string
  roles: RoleBrief[]
}

export interface RoleRow {
  id: number
  code: string
  name: string
  data_scope: string
  remark?: string
  status: string
  permissions: { code: string; name: string }[]
}

export interface DashboardData {
  overview: {
    project_count: number
    ongoing_count: number
    contract_amount: string
    received_amount: string
    cost_amount: string
    profit_amount: string
    receivable_amount: string
    alert_count: number
    pending_alert_count: number
  }
  project_profit_rank: Array<{
    id: number
    name: string
    contract_amount: number
    received_amount: number
    cost_amount: number
    profit: number
    receivable: number
  }>
  alert_by_source: { name: string; value: number }[]
  alert_by_level: { name: string; value: number }[]
  project_by_status: { name: string; value: number }[]
  modules?: ModuleOverview | null
}

export interface ModuleOverview {
  qualification: { total: number; valid: number; expiring: number; expired: number; health_score: number }
  document: { required_total: number; approved: number; missing: number; completeness: number }
  cost: { total_budget: string; total_actual: string; deviation_rate: number; over_budget_projects: number; pending_approval: number }
  finance: { total_income: string; total_expense: string; total_tax: string; net_profit: string; no_invoice_ratio: number }
  receivable: { total_outstanding: string; overdue_outstanding: string; overdue: number; stagnant: number; bad_debt_risk: number; worst_client?: string | null; worst_client_level?: string | null }
  bid: { total: number; bidded: number; won: number; win_rate: number; deposit_outstanding: string; deposit_overdue: number }
  labor: { total: number; onsite: number; contract_missing: number; insurance_missing: number; risk_workers: number; unpaid_amount: string }
}

export interface Qualification {
  id: number
  name: string
  type?: string
  level?: string
  cert_no?: string
  issuing_authority?: string
  scope?: string
  region_limit?: string
  valid_from?: string
  valid_to?: string
  annual_review_date?: string
  verify_status: string
  status: string
  secret_level: string
  owner_id?: number
  owner?: { id: number; name: string }
  file_id?: number
  remark?: string
  created_at: string
  days_to_expire?: number | null
}

export interface VerifyRecord {
  id: number
  qualification_id: number
  result: string
  method?: string
  remark?: string
  operator_name?: string
  created_at: string
}

export interface ScanResult {
  scanned: number
  expiring: number
  expired: number
  alerts_created: number
}

export interface DocTemplate {
  id: number
  name: string
  category?: string
  specialty?: string
  stage?: string
  required: boolean
  sort: number
  remark?: string
}

export interface DocItem {
  id: number
  project_id: number
  name: string
  category?: string
  specialty?: string
  stage?: string
  required: boolean
  due_date?: string
  status: string
  version: number
  file_id?: number
  uploader?: { id: number; name: string }
  reviewer?: { id: number; name: string }
  review_remark?: string
  secret_level: string
  remark?: string
  created_at: string
  overdue: boolean
}

export interface Completeness {
  project_id: number
  total: number
  required_total: number
  approved: number
  pending_upload: number
  pending_review: number
  returned: number
  missing: number
  completeness: number
}

export interface DocScanResult {
  scanned: number
  missing: number
  alerts_created: number
}

export interface Budget {
  id: number
  project_id: number
  category: string
  budget_amount: string
  remark?: string
  created_at: string
}

export interface Expense {
  id: number
  project_id: number
  category?: string
  type: string
  amount: string
  payee?: string
  expense_date?: string
  has_invoice: boolean
  status: string
  over_budget: boolean
  applicant?: { id: number; name: string }
  approver_id?: number
  approve_remark?: string
  remark?: string
  created_at: string
}

export interface BudgetDeviation {
  category: string
  budget_amount: string
  actual_amount: string
  remaining: string
  deviation_rate: number
  over_budget: boolean
}

export interface CostSummary {
  project_id: number
  total_budget: string
  total_actual: string
  total_remaining: string
  deviation_rate: number
  pending_approval: number
  no_invoice_amount: string
  deviations: BudgetDeviation[]
}

export interface FinanceRecord {
  id: number
  project_id: number
  direction: string
  category?: string
  amount: string
  tax_rate: string
  tax_amount: string
  has_invoice: boolean
  invoice_no?: string
  counterparty?: string
  record_date?: string
  status: string
  risk_tag?: string
  remark?: string
  created_at: string
}

export interface ProfitStatement {
  project_id: number
  total_income: string
  total_expense: string
  total_tax: string
  gross_profit: string
  net_profit: string
  net_margin: number
  invoiced_income: string
  no_invoice_expense: string
  no_invoice_ratio: number
}

export interface FinanceScanResult {
  scanned: number
  no_invoice_expense: string
  total_expense: string
  no_invoice_ratio: number
  flagged: number
  alerts_created: number
}

export interface Receivable {
  id: number
  project_id?: number
  project?: { id: number; code: string; name: string }
  client_id?: number
  client?: { id: number; name: string; credit_rating?: string }
  debt_type: string
  contract_no?: string
  amount: string
  received_amount: string
  outstanding: string
  due_date?: string
  overdue_days: number
  stage?: string
  status: string
  owner?: { id: number; name: string }
  evidence_file_id?: number
  remark?: string
  created_at: string
}

export interface CollectionLog {
  id: number
  receivable_id: number
  type: string
  content?: string
  result?: string
  amount?: string
  operator_name?: string
  created_at: string
}

export interface ReceivableScanResult {
  scanned: number
  overdue: number
  stagnant: number
  bad_debt_risk: number
  alerts_created: number
}

export interface ReceivableTier {
  name: string
  count: number
  outstanding: string
}

export interface ClientCredit {
  client_id?: number
  client_name: string
  total_amount: string
  received_amount: string
  outstanding: string
  overdue_outstanding: string
  credit_score: number
  credit_level: string
}

export interface ReceivableSummary {
  total_amount: string
  total_received: string
  total_outstanding: string
  overdue_outstanding: string
  tiers: ReceivableTier[]
  clients: ClientCredit[]
}

export interface Tender {
  id: number
  name: string
  source?: string
  project_type?: string
  region?: string
  qualification_req?: string
  region_req?: string
  registration_deadline?: string
  bid_open_time?: string
  deposit_amount: string
  deposit_due?: string
  deposit_returned: boolean
  status: string
  eval_reason?: string
  fail_reason?: string
  competitor_info?: string
  win_amount: string
  owner?: { id: number; name: string }
  secret_level: string
  remark?: string
  created_at: string
}

export interface TenderEvalResult {
  can_bid: boolean
  reasons: string[]
  status: string
}

export interface TenderBoard {
  total: number
  by_status: { name: string; value: number }[]
  bidded: number
  won: number
  win_rate: number
  deposit_outstanding: string
  deposit_overdue: number
}

export interface DepositScanResult {
  scanned: number
  overdue: number
  alerts_created: number
}

export interface Worker {
  id: number
  project_id?: number
  project?: { id: number; code: string; name: string }
  name: string
  id_card?: string
  team?: string
  craft?: string
  entry_date?: string
  status: string
  contract_signed: boolean
  insurance_expiry?: string
  bank_account?: string
  risk_tag?: string
  owner_id?: number
  remark?: string
  created_at: string
}

export interface PayrollRecord {
  id: number
  worker_id: number
  period: string
  amount: string
  paid: boolean
  pay_date?: string
  bank_flow_no?: string
  remark?: string
  created_at: string
}

export interface LaborScanResult {
  scanned: number
  contract_missing: number
  insurance_missing: number
  flagged: number
  alerts_created: number
}

export interface LaborSummary {
  total: number
  onsite: number
  contract_missing: number
  insurance_missing: number
  risk_workers: number
  unpaid_amount: string
  by_team: { name: string; value: number }[]
}
