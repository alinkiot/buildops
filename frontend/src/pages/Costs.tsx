import { useEffect, useState, useCallback } from 'react'
import {
  Table, Tag, Space, Select, Button, Modal, Form, Input, InputNumber, DatePicker,
  message, Row, Col, Card, Statistic, Progress, Tabs, Switch, Empty, Popconfirm,
} from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import http from '../api/client'
import type { ApiResponse, PageResult, Project, Budget, Expense, CostSummary } from '../api/types'
import { EXPENSE_TYPE, EXPENSE_STATUS, fmtMoney } from '../constants'
import { useAuth } from '../auth/AuthContext'

const typeOptions = Object.entries(EXPENSE_TYPE).map(([v, l]) => ({ value: v, label: l }))

export default function Costs() {
  const { has } = useAuth()
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState<number | undefined>()
  const [summary, setSummary] = useState<CostSummary | null>(null)
  const [budgets, setBudgets] = useState<Budget[]>([])
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [loading, setLoading] = useState(false)
  const [budgetOpen, setBudgetOpen] = useState(false)
  const [expenseOpen, setExpenseOpen] = useState(false)
  const [budgetForm] = Form.useForm()
  const [expenseForm] = Form.useForm()

  const canManage = has('cost:manage')
  const canApprove = has('cost:approve')

  useEffect(() => {
    http.get<ApiResponse<PageResult<Project>>>('/projects', { params: { page_size: 100 } }).then(({ data }) => {
      setProjects(data.data.items)
      if (data.data.items.length) setProjectId(data.data.items[0].id)
    })
  }, [])

  const load = useCallback(() => {
    if (!projectId) return
    setLoading(true)
    Promise.all([
      http.get<ApiResponse<CostSummary>>('/costs/summary', { params: { project_id: projectId } }),
      http.get<ApiResponse<Budget[]>>('/costs/budgets', { params: { project_id: projectId } }),
      http.get<ApiResponse<PageResult<Expense>>>('/costs/expenses', { params: { project_id: projectId, page_size: 100 } }),
    ])
      .then(([s, b, e]) => {
        setSummary(s.data.data)
        setBudgets(b.data.data)
        setExpenses(e.data.data.items)
      })
      .finally(() => setLoading(false))
  }, [projectId])

  useEffect(() => { load() }, [load])

  const addBudget = async () => {
    const v = await budgetForm.validateFields()
    await http.post('/costs/budgets', { ...v, project_id: projectId, budget_amount: String(v.budget_amount) })
    message.success('预算科目已添加')
    setBudgetOpen(false)
    budgetForm.resetFields()
    load()
  }

  const addExpense = async () => {
    const v = await expenseForm.validateFields()
    const { data } = await http.post<ApiResponse<Expense>>('/costs/expenses', {
      ...v,
      project_id: projectId,
      amount: String(v.amount),
      expense_date: v.expense_date ? v.expense_date.format('YYYY-MM-DD') : undefined,
    })
    if (data.data.over_budget) {
      message.warning('该支出导致科目超预算，已转入待审批并生成预警')
    } else {
      message.success('支出已登记')
    }
    setExpenseOpen(false)
    expenseForm.resetFields()
    load()
  }

  const approve = async (e: Expense, approved: boolean) => {
    await http.post(`/costs/expenses/${e.id}/approve`, { approved })
    message.success(approved ? '已审批通过' : '已驳回')
    load()
  }

  const budgetTab = (
    <>
      {canManage && (
        <Button type="primary" ghost icon={<PlusOutlined />} style={{ marginBottom: 16 }} onClick={() => setBudgetOpen(true)}>
          新增预算科目
        </Button>
      )}
      <Table
        rowKey="category"
        loading={loading}
        pagination={false}
        dataSource={summary?.deviations || []}
        columns={[
          { title: '成本科目', dataIndex: 'category' },
          { title: '预算金额', dataIndex: 'budget_amount', render: fmtMoney },
          { title: '已发生', dataIndex: 'actual_amount', render: fmtMoney },
          { title: '剩余额度', dataIndex: 'remaining', render: (v: string) => <span style={{ color: parseFloat(v) < 0 ? '#f5222d' : undefined }}>{fmtMoney(v)}</span> },
          {
            title: '执行进度 / 偏差',
            width: 260,
            render: (_, r) => {
              const pct = parseFloat(r.budget_amount) > 0
                ? Math.round((parseFloat(r.actual_amount) / parseFloat(r.budget_amount)) * 100)
                : 0
              return (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Progress
                    percent={Math.min(pct, 100)}
                    size="small"
                    status={r.over_budget ? 'exception' : 'normal'}
                    style={{ width: 120, margin: 0 }}
                  />
                  <span style={{ color: r.over_budget ? '#f5222d' : '#52c41a' }}>
                    {r.deviation_rate > 0 ? '+' : ''}{r.deviation_rate}%
                  </span>
                  {r.over_budget && <Tag color="red">超预算</Tag>}
                </div>
              )
            },
          },
        ]}
      />
    </>
  )

  const expenseTab = (
    <>
      {canManage && (
        <Button type="primary" ghost icon={<PlusOutlined />} style={{ marginBottom: 16 }} onClick={() => setExpenseOpen(true)}>
          登记支出
        </Button>
      )}
      <Table
        scroll={{ x: 'max-content' }}
        rowKey="id"
        loading={loading}
        pagination={false}
        dataSource={expenses}
        columns={[
          { title: '科目', dataIndex: 'category', width: 100, render: (v) => v || '-' },
          { title: '类型', dataIndex: 'type', width: 80, render: (t) => EXPENSE_TYPE[t] || t },
          { title: '金额', dataIndex: 'amount', width: 110, render: fmtMoney },
          { title: '供应商/分包商', dataIndex: 'payee', render: (v) => v || '-' },
          { title: '发票', dataIndex: 'has_invoice', width: 80, render: (v) => (v ? <Tag color="green">有票</Tag> : <Tag color="orange">无票</Tag>) },
          { title: '日期', dataIndex: 'expense_date', width: 110, render: (v) => v || '-' },
          {
            title: '状态',
            dataIndex: 'status',
            width: 100,
            render: (s, r) => (
              <span>
                <Tag color={EXPENSE_STATUS[s]?.color}>{EXPENSE_STATUS[s]?.label || s}</Tag>
                {r.over_budget && <Tag color="red">超预算</Tag>}
              </span>
            ),
          },
          {
            title: '操作',
            width: 130,
            fixed: 'right',
            render: (_, r) =>
              r.status === 'pending_approval' && canApprove ? (
                <Space>
                  <Popconfirm title="审批通过该支出？" onConfirm={() => approve(r, true)}>
                    <a>通过</a>
                  </Popconfirm>
                  <Popconfirm title="驳回该支出？" onConfirm={() => approve(r, false)}>
                    <a style={{ color: '#f5222d' }}>驳回</a>
                  </Popconfirm>
                </Space>
              ) : r.status === 'pending_approval' ? (
                <span style={{ color: '#999' }}>待上级审批</span>
              ) : '-',
          },
        ]}
      />
    </>
  )

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <span>项目：</span>
        <Select
          style={{ width: 280 }}
          value={projectId}
          onChange={setProjectId}
          options={projects.map((p) => ({ value: p.id, label: `${p.code} ${p.name}` }))}
          showSearch
          optionFilterProp="label"
          placeholder="请选择项目"
        />
      </Space>

      {summary && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={12} lg={5}><Card size="small"><Statistic title="总预算" value={fmtMoney(summary.total_budget)} /></Card></Col>
          <Col xs={12} lg={5}><Card size="small"><Statistic title="已发生成本" value={fmtMoney(summary.total_actual)} /></Card></Col>
          <Col xs={12} lg={5}>
            <Card size="small">
              <Statistic title="总偏差率" value={summary.deviation_rate} suffix="%"
                valueStyle={{ color: summary.deviation_rate > 0 ? '#f5222d' : '#52c41a' }} />
            </Card>
          </Col>
          <Col xs={12} lg={4}><Card size="small"><Statistic title="待审批" value={summary.pending_approval} valueStyle={{ color: summary.pending_approval > 0 ? '#fa8c16' : undefined }} /></Card></Col>
          <Col xs={12} lg={5}><Card size="small"><Statistic title="无票支出" value={fmtMoney(summary.no_invoice_amount)} valueStyle={{ color: '#fa8c16' }} /></Card></Col>
        </Row>
      )}

      {!projectId ? (
        <Empty description="请选择项目" />
      ) : (
        <Tabs
          items={[
            { key: 'budget', label: '预算与偏差', children: budgetTab },
            { key: 'expense', label: '支出登记', children: expenseTab },
          ]}
        />
      )}

      <Modal title="新增预算科目" open={budgetOpen} onOk={addBudget} onCancel={() => setBudgetOpen(false)} destroyOnClose>
        <Form form={budgetForm} layout="vertical">
          <Form.Item name="category" label="成本科目" rules={[{ required: true }]}>
            <Input placeholder="如 材料费 / 人工费 / 机械费 / 分包费" />
          </Form.Item>
          <Form.Item name="budget_amount" label="预算金额（元）" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} min={0} step={10000} />
          </Form.Item>
          <Form.Item name="remark" label="备注"><Input /></Form.Item>
        </Form>
      </Modal>

      <Modal title="登记支出" open={expenseOpen} onOk={addExpense} onCancel={() => setExpenseOpen(false)} destroyOnClose>
        <Form form={expenseForm} layout="vertical" initialValues={{ type: 'material', has_invoice: true }}>
          <Form.Item name="category" label="成本科目">
            <Select
              allowClear
              placeholder="关联预算科目（不选则不参与超预算检测）"
              options={budgets.map((b) => ({ value: b.category, label: `${b.category}（预算 ${fmtMoney(b.budget_amount)}）` }))}
            />
          </Form.Item>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="type" label="支出类型" style={{ flex: 1 }}><Select options={typeOptions} /></Form.Item>
            <Form.Item name="amount" label="金额（元）" style={{ flex: 1 }} rules={[{ required: true }]}>
              <InputNumber style={{ width: '100%' }} min={0} step={10000} />
            </Form.Item>
          </Space>
          <Form.Item name="payee" label="供应商 / 分包商"><Input /></Form.Item>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="expense_date" label="支出日期" style={{ flex: 1 }}><DatePicker style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="has_invoice" label="是否有票" valuePropName="checked" style={{ flex: 1 }}>
              <Switch checkedChildren="有票" unCheckedChildren="无票" defaultChecked />
            </Form.Item>
          </Space>
          <Form.Item name="remark" label="备注"><Input.TextArea rows={2} /></Form.Item>
          <div style={{ color: '#999', fontSize: 12 }}>提示：若选了成本科目且累计支出超过该科目预算，将自动转入待审批并向预警中心推送超预算预警（R-003）。</div>
        </Form>
      </Modal>
    </div>
  )
}
