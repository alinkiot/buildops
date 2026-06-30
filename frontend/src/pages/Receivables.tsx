import { useEffect, useState, useCallback } from 'react'
import {
  Table, Tag, Space, Select, Button, Modal, Form, Input, InputNumber, DatePicker,
  message, Row, Col, Card, Statistic, Tabs, Drawer, Timeline, Empty, Tooltip, Switch,
} from 'antd'
import { PlusOutlined, SyncOutlined, FileTextOutlined, DollarOutlined, MessageOutlined } from '@ant-design/icons'
import http from '../api/client'
import { downloadCsv } from '../api/client'
import type {
  ApiResponse, PageResult, Receivable, CollectionLog, ReceivableSummary, ReceivableScanResult,
} from '../api/types'
import { DEBT_TYPE, RECEIVABLE_STATUS, COLLECTION_LOG_TYPE, CREDIT_COLOR, fmtMoney } from '../constants'
import { useAuth } from '../auth/AuthContext'

const debtOptions = Object.entries(DEBT_TYPE).map(([v, l]) => ({ value: v, label: l }))
const statusOptions = Object.entries(RECEIVABLE_STATUS).map(([v, o]) => ({ value: v, label: o.label }))
const logTypeOptions = Object.entries(COLLECTION_LOG_TYPE).map(([v, l]) => ({ value: v, label: l }))

function overdueTag(days: number) {
  if (days <= 0) return <span style={{ color: '#999' }}>-</span>
  if (days > 180) return <Tag color="red">{days} 天</Tag>
  if (days > 90) return <Tag color="volcano">{days} 天</Tag>
  return <Tag color="orange">{days} 天</Tag>
}

export default function Receivables() {
  const { has } = useAuth()
  const [rows, setRows] = useState<Receivable[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string | undefined>()
  const [summary, setSummary] = useState<ReceivableSummary | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [payTarget, setPayTarget] = useState<Receivable | null>(null)
  const [logTarget, setLogTarget] = useState<Receivable | null>(null)
  const [logs, setLogs] = useState<CollectionLog[]>([])
  const [letter, setLetter] = useState<{ title: string; content: string } | null>(null)
  const [createForm] = Form.useForm()
  const [payForm] = Form.useForm()
  const [logForm] = Form.useForm()

  const canManage = has('receivable:manage')

  const loadList = useCallback(() => {
    setLoading(true)
    http.get<ApiResponse<PageResult<Receivable>>>('/receivables', { params: { status, page, page_size: 10 } })
      .then(({ data }) => { setRows(data.data.items); setTotal(data.data.total) })
      .finally(() => setLoading(false))
  }, [status, page])

  const loadSummary = useCallback(() => {
    http.get<ApiResponse<ReceivableSummary>>('/receivables/summary').then(({ data }) => setSummary(data.data))
  }, [])

  useEffect(() => { loadList() }, [loadList])
  useEffect(() => { loadSummary() }, [loadSummary])

  const refresh = () => { loadList(); loadSummary() }

  const createReceivable = async () => {
    const v = await createForm.validateFields()
    await http.post('/receivables', {
      ...v,
      amount: String(v.amount),
      due_date: v.due_date ? v.due_date.format('YYYY-MM-DD') : undefined,
    })
    message.success('债权已建档')
    setCreateOpen(false)
    createForm.resetFields()
    refresh()
  }

  const submitPayment = async () => {
    const v = await payForm.validateFields()
    await http.post(`/receivables/${payTarget!.id}/payment`, {
      amount: String(v.amount),
      sync_finance: v.sync_finance,
      record_date: v.record_date ? v.record_date.format('YYYY-MM-DD') : undefined,
      remark: v.remark,
    })
    message.success('回款已登记' + (v.sync_finance ? '，并已同步财税收入' : ''))
    setPayTarget(null)
    payForm.resetFields()
    refresh()
  }

  const openLogs = async (r: Receivable) => {
    setLogTarget(r)
    logForm.resetFields()
    logForm.setFieldsValue({ type: 'phone' })
    const { data } = await http.get<ApiResponse<CollectionLog[]>>(`/receivables/${r.id}/logs`)
    setLogs(data.data)
  }
  const addLog = async () => {
    const v = await logForm.validateFields()
    await http.post(`/receivables/${logTarget!.id}/logs`, v)
    message.success('催收日志已记录')
    const { data } = await http.get<ApiResponse<CollectionLog[]>>(`/receivables/${logTarget!.id}/logs`)
    setLogs(data.data)
    logForm.resetFields()
    logForm.setFieldsValue({ type: 'phone' })
  }

  const showLetter = async (r: Receivable, kind: string) => {
    const { data } = await http.get<ApiResponse<{ title: string; content: string }>>(`/receivables/${r.id}/letter`, { params: { kind } })
    setLetter(data.data)
  }

  const scan = async () => {
    const { data } = await http.post<ApiResponse<ReceivableScanResult>>('/receivables/scan')
    const r = data.data
    Modal.warning({
      title: '逾期分级扫描完成',
      content: `扫描 ${r.scanned} 笔债权 —— 逾期 ${r.overdue}、呆滞 ${r.stagnant}、坏账风险 ${r.bad_debt_risk}；生成预警 ${r.alerts_created} 条（已推送预警中心）。`,
    })
    refresh()
  }

  const ledgerTab = (
    <>
      <Space style={{ marginBottom: 16 }} wrap>
        <Select placeholder="状态" allowClear options={statusOptions} value={status}
          onChange={(v) => { setStatus(v); setPage(1) }} style={{ width: 140 }} />
        {canManage && (
          <>
            <Button type="primary" ghost icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新增债权</Button>
            <Button icon={<SyncOutlined />} onClick={scan}>逾期扫描</Button>
          </>
        )}
        <Button onClick={() => downloadCsv('/export/receivables', 'receivables.csv')}>导出 CSV</Button>
      </Space>
      <Table
        scroll={{ x: 'max-content' }}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={{ current: page, pageSize: 10, total, onChange: setPage }}
        columns={[
          { title: '甲方', dataIndex: ['client', 'name'], render: (v) => v || '-' },
          { title: '项目', dataIndex: ['project', 'name'], ellipsis: true, render: (v) => v || '-' },
          { title: '欠款类型', dataIndex: 'debt_type', width: 100, render: (t) => DEBT_TYPE[t] || t },
          { title: '欠款金额', dataIndex: 'amount', width: 110, render: fmtMoney },
          { title: '已回款', dataIndex: 'received_amount', width: 100, render: fmtMoney },
          { title: '待回款', dataIndex: 'outstanding', width: 110, render: (v: string) => <b>{fmtMoney(v)}</b> },
          { title: '逾期', dataIndex: 'overdue_days', width: 90, render: overdueTag },
          {
            title: '状态', dataIndex: 'status', width: 100,
            render: (s) => <Tag color={RECEIVABLE_STATUS[s]?.color}>{RECEIVABLE_STATUS[s]?.label || s}</Tag>,
          },
          {
            title: '操作',
            width: 250,
            fixed: 'right',
            render: (_, r) => (
              <Space size="small">
                <a onClick={() => openLogs(r)}><MessageOutlined /> 催收</a>
                {canManage && r.status !== 'settled' && r.status !== 'written_off' && (
                  <a onClick={() => { setPayTarget(r); payForm.setFieldsValue({ sync_finance: true }) }}><DollarOutlined /> 回款</a>
                )}
                <a onClick={() => showLetter(r, 'reminder')}><FileTextOutlined /> 催款函</a>
                <a onClick={() => showLetter(r, 'lawyer')}>律师函</a>
              </Space>
            ),
          },
        ]}
      />
    </>
  )

  const creditTab = summary && (
    <>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {summary.tiers.map((t) => (
          <Col xs={8} key={t.name}>
            <Card size="small">
              <Statistic
                title={`${t.name}（${t.count} 笔）`}
                value={fmtMoney(t.outstanding)}
                valueStyle={{ color: t.name === '坏账风险' ? '#f5222d' : t.name === '呆滞' ? '#fa541c' : '#fa8c16' }}
              />
            </Card>
          </Col>
        ))}
      </Row>
      <Table
        rowKey="client_name"
        pagination={false}
        dataSource={summary.clients}
        columns={[
          { title: '甲方', dataIndex: 'client_name' },
          { title: '债权总额', dataIndex: 'total_amount', render: fmtMoney },
          { title: '已回款', dataIndex: 'received_amount', render: fmtMoney },
          { title: '待回款', dataIndex: 'outstanding', render: fmtMoney },
          { title: '逾期未收', dataIndex: 'overdue_outstanding', render: (v: string) => <span style={{ color: parseFloat(v) > 0 ? '#f5222d' : undefined }}>{fmtMoney(v)}</span> },
          { title: '信用分', dataIndex: 'credit_score', width: 90 },
          { title: '信用等级', dataIndex: 'credit_level', width: 90, render: (l: string) => <Tag color={CREDIT_COLOR[l]}>{l} 级</Tag> },
        ]}
      />
    </>
  )

  return (
    <div>
      {summary && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={12} lg={6}><Card size="small"><Statistic title="债权总额" value={fmtMoney(summary.total_amount)} /></Card></Col>
          <Col xs={12} lg={6}><Card size="small"><Statistic title="累计已回款" value={fmtMoney(summary.total_received)} valueStyle={{ color: '#52c41a' }} /></Card></Col>
          <Col xs={12} lg={6}><Card size="small"><Statistic title="待回款" value={fmtMoney(summary.total_outstanding)} valueStyle={{ color: '#fa8c16' }} /></Card></Col>
          <Col xs={12} lg={6}><Card size="small"><Statistic title="逾期未收" value={fmtMoney(summary.overdue_outstanding)} valueStyle={{ color: '#f5222d' }} /></Card></Col>
        </Row>
      )}

      <Tabs
        items={[
          { key: 'ledger', label: '债权台账', children: ledgerTab },
          { key: 'credit', label: '汇总与甲方信用', children: creditTab || <Empty /> },
        ]}
      />

      <Modal title="新增债权" open={createOpen} onOk={createReceivable} onCancel={() => setCreateOpen(false)} destroyOnClose width={560}>
        <Form form={createForm} layout="vertical" initialValues={{ debt_type: 'progress', status: 'normal' }}>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="debt_type" label="欠款类型" style={{ flex: 1 }}><Select options={debtOptions} /></Form.Item>
            <Form.Item name="amount" label="欠款金额（元）" style={{ flex: 1 }} rules={[{ required: true }]}>
              <InputNumber style={{ width: '100%' }} min={0} step={10000} />
            </Form.Item>
          </Space>
          <Form.Item name="contract_no" label="合同编号"><Input /></Form.Item>
          <Form.Item name="due_date" label="应收到期日"><DatePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="stage" label="催收阶段"><Input placeholder="正常跟进/对账催收/函件催告" /></Form.Item>
          <Form.Item name="remark" label="备注"><Input.TextArea rows={2} /></Form.Item>
          <div style={{ color: '#999', fontSize: 12 }}>提示：项目/甲方可在债权建档后通过编辑关联（此处简化）。</div>
        </Form>
      </Modal>

      <Modal title={`登记回款 - ${payTarget?.client?.name || ''}`} open={!!payTarget} onOk={submitPayment} onCancel={() => setPayTarget(null)} destroyOnClose>
        {payTarget && (
          <div style={{ marginBottom: 12, color: '#555' }}>
            待回款：<b>{fmtMoney(payTarget.outstanding)}</b>（{DEBT_TYPE[payTarget.debt_type]}）
          </div>
        )}
        <Form form={payForm} layout="vertical">
          <Form.Item name="amount" label="本次回款金额（元）" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} min={0} step={10000} />
          </Form.Item>
          <Form.Item name="record_date" label="回款日期"><DatePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="sync_finance" label="同步生成财税收入流水" valuePropName="checked" initialValue={true}>
            <Switch checkedChildren="同步" unCheckedChildren="不同步" defaultChecked />
          </Form.Item>
          <Form.Item name="remark" label="备注"><Input /></Form.Item>
        </Form>
      </Modal>

      <Drawer title={`催收记录 - ${logTarget?.client?.name || ''}`} open={!!logTarget} onClose={() => setLogTarget(null)} width={520}>
        {canManage && (
          <Form form={logForm} layout="inline" style={{ marginBottom: 16 }} onFinish={addLog}>
            <Form.Item name="type" rules={[{ required: true }]}>
              <Select options={logTypeOptions} style={{ width: 100 }} />
            </Form.Item>
            <Form.Item name="content" style={{ flex: 1, minWidth: 180 }}>
              <Input placeholder="沟通内容" />
            </Form.Item>
            <Form.Item name="result"><Input placeholder="结果" style={{ width: 100 }} /></Form.Item>
            <Form.Item><Button type="primary" htmlType="submit">记录</Button></Form.Item>
          </Form>
        )}
        {logs.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无催收记录" />
        ) : (
          <Timeline
            items={logs.map((l) => ({
              color: l.type === 'payment' ? 'green' : l.type === 'letter' ? 'red' : 'blue',
              children: (
                <div>
                  <Tag>{COLLECTION_LOG_TYPE[l.type] || l.type}</Tag>
                  {l.amount && <Tag color="green">回款 {fmtMoney(l.amount)}</Tag>}
                  <div style={{ fontSize: 13 }}>{l.content}</div>
                  {l.result && <div style={{ fontSize: 12, color: '#888' }}>结果：{l.result}</div>}
                  <div style={{ fontSize: 12, color: '#aaa' }}>{l.operator_name} · {new Date(l.created_at).toLocaleString('zh-CN')}</div>
                </div>
              ),
            }))}
          />
        )}
      </Drawer>

      <Modal title={letter?.title} open={!!letter} onCancel={() => setLetter(null)} footer={<Button onClick={() => setLetter(null)}>关闭</Button>} width={600}>
        <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', background: '#fafafa', padding: 16, borderRadius: 6, lineHeight: 1.8 }}>
          {letter?.content}
        </pre>
        <Tooltip title="MVP 生成文本，可复制到 Word 用印">
          <span style={{ color: '#999', fontSize: 12 }}>* 文书内容由系统按债权数据自动生成</span>
        </Tooltip>
      </Modal>
    </div>
  )
}
