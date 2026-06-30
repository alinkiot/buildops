import { useEffect, useState, useCallback } from 'react'
import {
  Table, Tag, Space, Select, Button, Modal, Form, Input, InputNumber, DatePicker,
  message, Row, Col, Card, Statistic, Popconfirm, Drawer, Switch, Empty,
} from 'antd'
import { PlusOutlined, SearchOutlined, SyncOutlined, DollarOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import http from '../api/client'
import type { ApiResponse, PageResult, Worker, PayrollRecord, LaborSummary, LaborScanResult } from '../api/types'
import { WORKER_STATUS, fmtMoney } from '../constants'
import { useAuth } from '../auth/AuthContext'

const statusOptions = Object.entries(WORKER_STATUS).map(([v, o]) => ({ value: v, label: o.label }))

export default function Labor() {
  const { has } = useAuth()
  const [rows, setRows] = useState<Worker[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string | undefined>()
  const [keyword, setKeyword] = useState('')
  const [summary, setSummary] = useState<LaborSummary | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Worker | null>(null)
  const [payTarget, setPayTarget] = useState<Worker | null>(null)
  const [payroll, setPayroll] = useState<PayrollRecord[]>([])
  const [form] = Form.useForm()
  const [payForm] = Form.useForm()

  const canManage = has('labor:manage')

  const loadSummary = useCallback(() => {
    http.get<ApiResponse<LaborSummary>>('/labor/summary').then(({ data }) => setSummary(data.data))
  }, [])
  const load = useCallback(() => {
    setLoading(true)
    http.get<ApiResponse<PageResult<Worker>>>('/labor/workers', { params: { status, keyword: keyword || undefined, page, page_size: 10 } })
      .then(({ data }) => { setRows(data.data.items); setTotal(data.data.total) })
      .finally(() => setLoading(false))
  }, [status, keyword, page])

  useEffect(() => { load() }, [load])
  useEffect(() => { loadSummary() }, [loadSummary])
  const refresh = () => { load(); loadSummary() }

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ status: 'onsite', contract_signed: true })
    setModalOpen(true)
  }
  const openEdit = (r: Worker) => {
    setEditing(r)
    form.setFieldsValue({
      ...r,
      entry_date: r.entry_date ? dayjs(r.entry_date) : undefined,
      insurance_expiry: r.insurance_expiry ? dayjs(r.insurance_expiry) : undefined,
    })
    setModalOpen(true)
  }
  const submit = async () => {
    const v = await form.validateFields()
    const payload = {
      ...v,
      entry_date: v.entry_date ? v.entry_date.format('YYYY-MM-DD') : undefined,
      insurance_expiry: v.insurance_expiry ? v.insurance_expiry.format('YYYY-MM-DD') : undefined,
    }
    try {
      if (editing) { await http.put(`/labor/workers/${editing.id}`, payload); message.success('已更新') }
      else { await http.post('/labor/workers', payload); message.success('已创建') }
      setModalOpen(false)
      refresh()
    } catch { /* 拦截器提示 */ }
  }
  const remove = async (id: number) => { await http.delete(`/labor/workers/${id}`); message.success('已删除'); refresh() }

  const scan = async () => {
    const { data } = await http.post<ApiResponse<LaborScanResult>>('/labor/scan')
    const r = data.data
    Modal.warning({
      title: '用工风险扫描完成',
      content: `扫描 ${r.scanned} 名工人 —— 无合同 ${r.contract_missing}、工伤保险缺失/过期 ${r.insurance_missing}；标记风险 ${r.flagged} 人，生成预警 ${r.alerts_created} 条（已推送预警中心）。`,
    })
    refresh()
  }

  const openPayroll = async (w: Worker) => {
    setPayTarget(w)
    payForm.resetFields()
    payForm.setFieldsValue({ period: dayjs().format('YYYY-MM'), paid: false })
    const { data } = await http.get<ApiResponse<PayrollRecord[]>>(`/labor/workers/${w.id}/payroll`)
    setPayroll(data.data)
  }
  const addPayroll = async () => {
    const v = await payForm.validateFields()
    await http.post(`/labor/workers/${payTarget!.id}/payroll`, {
      ...v, amount: String(v.amount), pay_date: v.pay_date ? v.pay_date.format('YYYY-MM-DD') : undefined,
    })
    message.success('工资记录已登记')
    const { data } = await http.get<ApiResponse<PayrollRecord[]>>(`/labor/workers/${payTarget!.id}/payroll`)
    setPayroll(data.data)
    payForm.resetFields()
    payForm.setFieldsValue({ period: dayjs().format('YYYY-MM'), paid: false })
  }

  return (
    <div>
      {summary && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={12} lg={4}><Card size="small"><Statistic title="工人总数" value={summary.total} /></Card></Col>
          <Col xs={12} lg={4}><Card size="small"><Statistic title="在场" value={summary.onsite} valueStyle={{ color: '#1677ff' }} /></Card></Col>
          <Col xs={12} lg={4}><Card size="small"><Statistic title="无劳动合同" value={summary.contract_missing} valueStyle={{ color: summary.contract_missing > 0 ? '#f5222d' : undefined }} /></Card></Col>
          <Col xs={12} lg={4}><Card size="small"><Statistic title="保险缺失/过期" value={summary.insurance_missing} valueStyle={{ color: summary.insurance_missing > 0 ? '#f5222d' : undefined }} /></Card></Col>
          <Col xs={12} lg={4}><Card size="small"><Statistic title="风险工人" value={summary.risk_workers} valueStyle={{ color: summary.risk_workers > 0 ? '#fa541c' : undefined }} /></Card></Col>
          <Col xs={12} lg={4}><Card size="small"><Statistic title="待发工资" value={fmtMoney(summary.unpaid_amount)} valueStyle={{ color: '#fa8c16' }} /></Card></Col>
        </Row>
      )}

      <Space style={{ marginBottom: 16 }} wrap>
        <Input placeholder="姓名" prefix={<SearchOutlined />} allowClear value={keyword}
          onChange={(e) => setKeyword(e.target.value)} onPressEnter={() => { setPage(1); load() }} style={{ width: 180 }} />
        <Select placeholder="状态" allowClear options={statusOptions} value={status}
          onChange={(v) => { setStatus(v); setPage(1) }} style={{ width: 120 }} />
        <Button type="primary" icon={<SearchOutlined />} onClick={() => { setPage(1); load() }}>查询</Button>
        {canManage && (
          <>
            <Button type="primary" ghost icon={<PlusOutlined />} onClick={openCreate}>新增工人</Button>
            <Button icon={<SyncOutlined />} onClick={scan}>用工风险扫描</Button>
          </>
        )}
      </Space>

      <Table
        scroll={{ x: 'max-content' }}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={{ current: page, pageSize: 10, total, onChange: setPage }}
        columns={[
          { title: '姓名', dataIndex: 'name', width: 90 },
          { title: '班组', dataIndex: 'team', width: 100, render: (v) => v || '-' },
          { title: '工种', dataIndex: 'craft', width: 90, render: (v) => v || '-' },
          { title: '项目', dataIndex: ['project', 'name'], ellipsis: true, render: (v) => v || '-' },
          { title: '入场日期', dataIndex: 'entry_date', width: 110, render: (v) => v || '-' },
          { title: '合同', dataIndex: 'contract_signed', width: 80, render: (v) => (v ? <Tag color="green">已签</Tag> : <Tag color="red">缺失</Tag>) },
          {
            title: '工伤保险', dataIndex: 'insurance_expiry', width: 120,
            render: (v: string | undefined) => {
              if (!v) return <Tag color="red">未参保</Tag>
              const expired = dayjs(v).isBefore(dayjs(), 'day')
              return <span style={{ color: expired ? '#f5222d' : undefined }}>{v}{expired && ' (过期)'}</span>
            },
          },
          {
            title: '状态', dataIndex: 'status', width: 90,
            render: (s, r) => (
              <span>
                <Tag color={WORKER_STATUS[s]?.color}>{WORKER_STATUS[s]?.label || s}</Tag>
                {r.risk_tag && <Tag color="red">{r.risk_tag}</Tag>}
              </span>
            ),
          },
          {
            title: '操作', width: 160, fixed: 'right',
            render: (_, r) => (
              <Space size="small">
                <a onClick={() => openPayroll(r)}><DollarOutlined /> 工资</a>
                {canManage && <a onClick={() => openEdit(r)}>编辑</a>}
                {canManage && (
                  <Popconfirm title="确认删除该工人？" onConfirm={() => remove(r.id)}>
                    <a style={{ color: '#f5222d' }}>删除</a>
                  </Popconfirm>
                )}
              </Space>
            ),
          },
        ]}
      />

      <Modal title={editing ? '编辑工人' : '新增工人'} open={modalOpen} onOk={submit} onCancel={() => setModalOpen(false)} width={600} destroyOnClose>
        <Form form={form} layout="vertical">
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="name" label="姓名" style={{ flex: 1 }} rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="id_card" label="身份证号" style={{ flex: 1 }}><Input /></Form.Item>
          </Space>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="team" label="班组" style={{ flex: 1 }}><Input /></Form.Item>
            <Form.Item name="craft" label="工种" style={{ flex: 1 }}><Input placeholder="钢筋工/木工/普工" /></Form.Item>
            <Form.Item name="status" label="状态" style={{ flex: 1 }}><Select options={statusOptions} /></Form.Item>
          </Space>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="entry_date" label="入场日期" style={{ flex: 1 }}><DatePicker style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="insurance_expiry" label="工伤保险到期" style={{ flex: 1 }} tooltip="留空表示未参保"><DatePicker style={{ width: '100%' }} /></Form.Item>
          </Space>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="contract_signed" label="已签劳动合同" valuePropName="checked" style={{ flex: 1 }}>
              <Switch checkedChildren="已签" unCheckedChildren="未签" />
            </Form.Item>
            <Form.Item name="bank_account" label="代发账户" style={{ flex: 2 }}><Input /></Form.Item>
          </Space>
          <Form.Item name="remark" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      <Drawer title={`工资记录 - ${payTarget?.name || ''}`} open={!!payTarget} onClose={() => setPayTarget(null)} width={520}>
        {canManage && (
          <Form form={payForm} layout="inline" style={{ marginBottom: 16 }} onFinish={addPayroll}>
            <Form.Item name="period" rules={[{ required: true }]}><Input placeholder="期间 2026-06" style={{ width: 110 }} /></Form.Item>
            <Form.Item name="amount" rules={[{ required: true }]}><InputNumber placeholder="金额" min={0} style={{ width: 110 }} /></Form.Item>
            <Form.Item name="paid" valuePropName="checked"><Switch checkedChildren="已发" unCheckedChildren="待发" /></Form.Item>
            <Form.Item><Button type="primary" htmlType="submit">登记</Button></Form.Item>
          </Form>
        )}
        {payroll.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无工资记录" />
        ) : (
          <Table
            rowKey="id" size="small" pagination={false} dataSource={payroll}
            columns={[
              { title: '期间', dataIndex: 'period' },
              { title: '金额', dataIndex: 'amount', render: (v: string) => `${parseFloat(v).toLocaleString('zh-CN')} 元` },
              { title: '状态', dataIndex: 'paid', render: (v) => (v ? <Tag color="green">已发放</Tag> : <Tag color="gold">待发</Tag>) },
              { title: '发放日', dataIndex: 'pay_date', render: (v) => v || '-' },
            ]}
          />
        )}
      </Drawer>
    </div>
  )
}
