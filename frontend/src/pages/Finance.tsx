import { useEffect, useState, useCallback } from 'react'
import {
  Table, Tag, Space, Select, Button, Modal, Form, Input, InputNumber, DatePicker,
  message, Row, Col, Card, Statistic, Tabs, Switch, Empty, Descriptions, Alert as AntAlert,
} from 'antd'
import { PlusOutlined, SyncOutlined } from '@ant-design/icons'
import http from '../api/client'
import type { ApiResponse, PageResult, Project, FinanceRecord, ProfitStatement, FinanceScanResult } from '../api/types'
import { FINANCE_STATUS, fmtMoney } from '../constants'
import { useAuth } from '../auth/AuthContext'

const directionOptions = [
  { value: 'income', label: '收入' },
  { value: 'expense', label: '支出' },
]

export default function Finance() {
  const { has } = useAuth()
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState<number | undefined>()
  const [profit, setProfit] = useState<ProfitStatement | null>(null)
  const [records, setRecords] = useState<FinanceRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [direction, setDirection] = useState<string | undefined>()
  const [recordOpen, setRecordOpen] = useState(false)
  const [form] = Form.useForm()

  const canManage = has('finance:manage')

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
      http.get<ApiResponse<ProfitStatement>>('/finance/profit', { params: { project_id: projectId } }),
      http.get<ApiResponse<PageResult<FinanceRecord>>>('/finance', { params: { project_id: projectId, direction, page_size: 100 } }),
    ])
      .then(([p, r]) => { setProfit(p.data.data); setRecords(r.data.data.items) })
      .finally(() => setLoading(false))
  }, [projectId, direction])

  useEffect(() => { load() }, [load])

  const addRecord = async () => {
    const v = await form.validateFields()
    const { data } = await http.post<ApiResponse<FinanceRecord>>('/finance', {
      ...v,
      project_id: projectId,
      amount: String(v.amount),
      tax_rate: v.tax_rate != null ? String(v.tax_rate) : '0',
      record_date: v.record_date ? v.record_date.format('YYYY-MM-DD') : undefined,
    })
    if (data.data.risk_tag === '无票') message.warning('已登记，无票支出已标记风险')
    else message.success('流水已登记')
    setRecordOpen(false)
    form.resetFields()
    load()
  }

  const scan = async () => {
    const { data } = await http.post<ApiResponse<FinanceScanResult>>('/finance/scan', null, { params: { project_id: projectId } })
    const r = data.data
    Modal.confirm({
      title: '财税风险扫描完成',
      content: (
        <div>
          <p>支出合计：{fmtMoney(r.total_expense)}</p>
          <p>无票支出：{fmtMoney(r.no_invoice_expense)}，占比 <b style={{ color: r.no_invoice_ratio > 10 ? '#f5222d' : '#52c41a' }}>{r.no_invoice_ratio}%</b>（阈值 10%）</p>
          <p>标记无票流水：{r.flagged} 条；生成预警：<b>{r.alerts_created}</b> 条</p>
        </div>
      ),
      okText: '知道了',
      cancelButtonProps: { style: { display: 'none' } },
    })
    load()
  }

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
        {canManage && projectId && <Button icon={<SyncOutlined />} onClick={scan}>财税风险扫描</Button>}
      </Space>

      {profit && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col xs={12} lg={5}><Card size="small"><Statistic title="收入合计" value={fmtMoney(profit.total_income)} valueStyle={{ color: '#52c41a' }} /></Card></Col>
            <Col xs={12} lg={5}><Card size="small"><Statistic title="支出合计" value={fmtMoney(profit.total_expense)} valueStyle={{ color: '#fa541c' }} /></Card></Col>
            <Col xs={12} lg={4}><Card size="small"><Statistic title="税费合计" value={fmtMoney(profit.total_tax)} /></Card></Col>
            <Col xs={12} lg={5}><Card size="small"><Statistic title="净利润" value={fmtMoney(profit.net_profit)} valueStyle={{ color: '#722ed1' }} /></Card></Col>
            <Col xs={12} lg={5}><Card size="small"><Statistic title="净利率" value={profit.net_margin} suffix="%" /></Card></Col>
          </Row>
          {profit.no_invoice_ratio > 10 && (
            <AntAlert
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
              message={`无票支出占比 ${profit.no_invoice_ratio}%，已超过 10% 阈值，存在税务风险（无票支出 ${fmtMoney(profit.no_invoice_expense)}）。建议补票或在风险扫描后处理预警。`}
            />
          )}
        </>
      )}

      {!projectId ? (
        <Empty description="请选择项目" />
      ) : (
        <Tabs
          tabBarExtraContent={
            canManage ? <Button type="primary" ghost icon={<PlusOutlined />} onClick={() => setRecordOpen(true)}>登记流水</Button> : null
          }
          items={[
            {
              key: 'all',
              label: '收支流水',
              children: (
                <>
                  <Space style={{ marginBottom: 12 }}>
                    <Select placeholder="收支方向" allowClear options={directionOptions} value={direction} onChange={setDirection} style={{ width: 130 }} />
                  </Space>
                  <Table
                    rowKey="id"
                    loading={loading}
                    pagination={false}
                    dataSource={records}
                    columns={[
                      { title: '日期', dataIndex: 'record_date', width: 110, render: (v) => v || '-' },
                      {
                        title: '方向', dataIndex: 'direction', width: 80,
                        render: (d) => <Tag color={d === 'income' ? 'green' : 'volcano'}>{d === 'income' ? '收入' : '支出'}</Tag>,
                      },
                      { title: '类别', dataIndex: 'category', width: 100, render: (v) => v || '-' },
                      { title: '金额', dataIndex: 'amount', width: 110, render: fmtMoney },
                      { title: '税率', dataIndex: 'tax_rate', width: 70, render: (v: string) => `${(parseFloat(v) * 100).toFixed(0)}%` },
                      { title: '税额', dataIndex: 'tax_amount', width: 100, render: fmtMoney },
                      {
                        title: '发票', dataIndex: 'has_invoice', width: 120,
                        render: (v, r) => (v ? <span><Tag color="green">有票</Tag>{r.invoice_no}</span> : <Tag color="orange">无票</Tag>),
                      },
                      { title: '对方主体', dataIndex: 'counterparty', render: (v) => v || '-' },
                      {
                        title: '状态', dataIndex: 'status', width: 90,
                        render: (s, r) => (
                          <span>
                            <Tag color={FINANCE_STATUS[s]?.color}>{FINANCE_STATUS[s]?.label || s}</Tag>
                            {r.risk_tag && <Tag color="red">{r.risk_tag}</Tag>}
                          </span>
                        ),
                      },
                    ]}
                  />
                </>
              ),
            },
            {
              key: 'profit',
              label: '利润表',
              children: profit && (
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="收入合计">{fmtMoney(profit.total_income)}</Descriptions.Item>
                  <Descriptions.Item label="其中已开票收入">{fmtMoney(profit.invoiced_income)}</Descriptions.Item>
                  <Descriptions.Item label="支出合计">{fmtMoney(profit.total_expense)}</Descriptions.Item>
                  <Descriptions.Item label="其中无票支出">{fmtMoney(profit.no_invoice_expense)}（{profit.no_invoice_ratio}%）</Descriptions.Item>
                  <Descriptions.Item label="税费合计">{fmtMoney(profit.total_tax)}</Descriptions.Item>
                  <Descriptions.Item label="毛利（收入-支出）">{fmtMoney(profit.gross_profit)}</Descriptions.Item>
                  <Descriptions.Item label="净利润（收入-支出-税费）"><b style={{ color: '#722ed1' }}>{fmtMoney(profit.net_profit)}</b></Descriptions.Item>
                  <Descriptions.Item label="净利率"><b>{profit.net_margin}%</b></Descriptions.Item>
                </Descriptions>
              ),
            },
          ]}
        />
      )}

      <Modal title="登记收支流水" open={recordOpen} onOk={addRecord} onCancel={() => setRecordOpen(false)} destroyOnClose width={560}>
        <Form form={form} layout="vertical" initialValues={{ direction: 'income', has_invoice: true, tax_rate: 0.09 }}>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="direction" label="收支方向" style={{ flex: 1 }} rules={[{ required: true }]}>
              <Select options={directionOptions} />
            </Form.Item>
            <Form.Item name="category" label="类别" style={{ flex: 1 }}><Input placeholder="进度款/材料款/税费" /></Form.Item>
          </Space>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="amount" label="金额（元）" style={{ flex: 1 }} rules={[{ required: true }]}>
              <InputNumber style={{ width: '100%' }} min={0} step={10000} />
            </Form.Item>
            <Form.Item name="tax_rate" label="税率" style={{ flex: 1 }}>
              <InputNumber style={{ width: '100%' }} min={0} max={1} step={0.01} />
            </Form.Item>
          </Space>
          <div style={{ color: '#999', fontSize: 12, marginBottom: 12 }}>税额留空将自动按 金额 × 税率 计算。</div>
          <Form.Item name="has_invoice" label="是否有票" valuePropName="checked">
            <Switch checkedChildren="有票" unCheckedChildren="无票" defaultChecked />
          </Form.Item>
          <Form.Item name="invoice_no" label="发票号"><Input /></Form.Item>
          <Form.Item name="counterparty" label="对方主体（开票/收票方）"><Input /></Form.Item>
          <Form.Item name="record_date" label="入账日期"><DatePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="remark" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
