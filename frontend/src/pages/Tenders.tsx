import { useEffect, useState, useCallback } from 'react'
import {
  Table, Tag, Space, Select, Button, Modal, Form, Input, InputNumber, DatePicker,
  message, Row, Col, Card, Statistic, Popconfirm, Tooltip,
} from 'antd'
import { PlusOutlined, SearchOutlined, SafetyOutlined, SyncOutlined, TrophyOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import http from '../api/client'
import type { ApiResponse, PageResult, Tender, TenderBoard, TenderEvalResult, DepositScanResult } from '../api/types'
import { TENDER_STATUS, fmtMoney } from '../constants'
import { useAuth } from '../auth/AuthContext'

const statusOptions = Object.entries(TENDER_STATUS).map(([v, o]) => ({ value: v, label: o.label }))

export default function Tenders() {
  const { has } = useAuth()
  const [rows, setRows] = useState<Tender[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string | undefined>()
  const [keyword, setKeyword] = useState('')
  const [board, setBoard] = useState<TenderBoard | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Tender | null>(null)
  const [form] = Form.useForm()

  const canManage = has('tender:manage')

  const loadBoard = useCallback(() => {
    http.get<ApiResponse<TenderBoard>>('/tenders/board').then(({ data }) => setBoard(data.data))
  }, [])

  const load = useCallback(() => {
    setLoading(true)
    http.get<ApiResponse<PageResult<Tender>>>('/tenders', { params: { status, keyword: keyword || undefined, page, page_size: 10 } })
      .then(({ data }) => { setRows(data.data.items); setTotal(data.data.total) })
      .finally(() => setLoading(false))
  }, [status, keyword, page])

  useEffect(() => { load() }, [load])
  useEffect(() => { loadBoard() }, [loadBoard])

  const refresh = () => { load(); loadBoard() }

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ status: 'pending_eval', deposit_amount: 0 })
    setModalOpen(true)
  }
  const openEdit = (r: Tender) => {
    setEditing(r)
    const d = (v?: string) => (v ? dayjs(v) : undefined)
    form.setFieldsValue({
      ...r, deposit_amount: parseFloat(r.deposit_amount), win_amount: parseFloat(r.win_amount),
      registration_deadline: d(r.registration_deadline), bid_open_time: d(r.bid_open_time), deposit_due: d(r.deposit_due),
    })
    setModalOpen(true)
  }

  const submit = async () => {
    const v = await form.validateFields()
    const fmt = (x: dayjs.Dayjs | undefined) => (x ? x.format('YYYY-MM-DD') : undefined)
    const payload = {
      ...v,
      deposit_amount: v.deposit_amount != null ? String(v.deposit_amount) : '0',
      win_amount: v.win_amount != null ? String(v.win_amount) : undefined,
      registration_deadline: fmt(v.registration_deadline),
      bid_open_time: fmt(v.bid_open_time),
      deposit_due: fmt(v.deposit_due),
    }
    try {
      if (editing) { await http.put(`/tenders/${editing.id}`, payload); message.success('已更新') }
      else { await http.post('/tenders', payload); message.success('已创建') }
      setModalOpen(false)
      refresh()
    } catch { /* 拦截器提示 */ }
  }

  const evaluate = async (r: Tender) => {
    const { data } = await http.post<ApiResponse<TenderEvalResult>>(`/tenders/${r.id}/evaluate`)
    const res = data.data
    Modal[res.can_bid ? 'success' : 'warning']({
      title: res.can_bid ? '准入校验通过：可投' : '准入校验：不可投',
      content: res.can_bid
        ? '企业现有有效资质满足该标的要求，可参与投标。'
        : <div><p>不满足条件（已生成预警 R-002）：</p><ul>{res.reasons.map((x, i) => <li key={i}>{x}</li>)}</ul></div>,
    })
    refresh()
  }

  const scanDeposit = async () => {
    const { data } = await http.post<ApiResponse<DepositScanResult>>('/tenders/scan-deposit')
    const r = data.data
    Modal.warning({
      title: '保证金到期扫描完成',
      content: `扫描 ${r.scanned} 个标的，保证金逾期未退 ${r.overdue} 笔，生成预警 ${r.alerts_created} 条（已推送预警中心）。`,
    })
    refresh()
  }

  const remove = async (id: number) => { await http.delete(`/tenders/${id}`); message.success('已删除'); refresh() }

  return (
    <div>
      {board && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={12} lg={4}><Card size="small"><Statistic title="标的总数" value={board.total} /></Card></Col>
          <Col xs={12} lg={4}><Card size="small"><Statistic title="有效投标" value={board.bidded} /></Card></Col>
          <Col xs={12} lg={4}><Card size="small"><Statistic title="已中标" value={board.won} prefix={<TrophyOutlined />} valueStyle={{ color: '#52c41a' }} /></Card></Col>
          <Col xs={12} lg={4}><Card size="small"><Statistic title="中标率" value={board.win_rate} suffix="%" valueStyle={{ color: '#1677ff' }} /></Card></Col>
          <Col xs={12} lg={4}><Card size="small"><Statistic title="未退保证金" value={fmtMoney(board.deposit_outstanding)} valueStyle={{ color: '#fa8c16' }} /></Card></Col>
          <Col xs={12} lg={4}><Card size="small"><Statistic title="保证金逾期" value={board.deposit_overdue} suffix="笔" valueStyle={{ color: board.deposit_overdue > 0 ? '#f5222d' : undefined }} /></Card></Col>
        </Row>
      )}

      <Space style={{ marginBottom: 16 }} wrap>
        <Input placeholder="标的名称" prefix={<SearchOutlined />} allowClear value={keyword}
          onChange={(e) => setKeyword(e.target.value)} onPressEnter={() => { setPage(1); load() }} style={{ width: 200 }} />
        <Select placeholder="状态" allowClear options={statusOptions} value={status}
          onChange={(v) => { setStatus(v); setPage(1) }} style={{ width: 140 }} />
        <Button type="primary" icon={<SearchOutlined />} onClick={() => { setPage(1); load() }}>查询</Button>
        {canManage && (
          <>
            <Button type="primary" ghost icon={<PlusOutlined />} onClick={openCreate}>新增标的</Button>
            <Button icon={<SyncOutlined />} onClick={scanDeposit}>保证金扫描</Button>
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
          {
            title: '标的名称', dataIndex: 'name', ellipsis: true,
            render: (t, r) => (
              <span>{t}{r.secret_level === 'classified' && <Tag color="red" style={{ marginLeft: 6 }}>涉密</Tag>}</span>
            ),
          },
          { title: '类型', dataIndex: 'project_type', width: 80, render: (v) => v || '-' },
          { title: '地域', dataIndex: 'region', width: 80, render: (v) => v || '-' },
          { title: '资质要求', dataIndex: 'qualification_req', width: 180, ellipsis: true, render: (v) => v || '-' },
          { title: '报名截止', dataIndex: 'registration_deadline', width: 110, render: (v) => v || '-' },
          { title: '保证金', dataIndex: 'deposit_amount', width: 100, render: (v: string, r) => (parseFloat(v) > 0 ? <span>{fmtMoney(v)}{!r.deposit_returned && <Tag color="orange" style={{ marginLeft: 4 }}>未退</Tag>}</span> : '-') },
          {
            title: '状态', dataIndex: 'status', width: 100,
            render: (s, r) => (
              <Tooltip title={r.eval_reason || ''}>
                <Tag color={TENDER_STATUS[s]?.color}>{TENDER_STATUS[s]?.label || s}</Tag>
              </Tooltip>
            ),
          },
          {
            title: '操作', width: 180, fixed: 'right',
            render: (_, r) =>
              canManage ? (
                <Space size="small">
                  <a onClick={() => evaluate(r)}><SafetyOutlined /> 准入校验</a>
                  <a onClick={() => openEdit(r)}>编辑</a>
                  <Popconfirm title="确认删除该标的？" onConfirm={() => remove(r.id)}>
                    <a style={{ color: '#f5222d' }}>删除</a>
                  </Popconfirm>
                </Space>
              ) : <span style={{ color: '#999' }}>-</span>,
          },
        ]}
      />

      <Modal title={editing ? '编辑标的' : '新增标的'} open={modalOpen} onOk={submit} onCancel={() => setModalOpen(false)} width={640} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="标的名称" rules={[{ required: true, message: '请输入标的名称' }]}><Input /></Form.Item>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="source" label="公告来源" style={{ flex: 1 }}><Input /></Form.Item>
            <Form.Item name="project_type" label="项目类型" style={{ flex: 1 }}><Input placeholder="市政/房建/公路" /></Form.Item>
            <Form.Item name="region" label="地域" style={{ flex: 1 }}><Input /></Form.Item>
          </Space>
          <Form.Item name="qualification_req" label="资质要求" tooltip="多项用空格或顿号分隔，准入校验将逐项匹配企业有效资质">
            <Input placeholder="如：市政公用工程施工总承包 安全生产许可证" />
          </Form.Item>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="registration_deadline" label="报名截止" style={{ flex: 1 }}><DatePicker style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="bid_open_time" label="开标时间" style={{ flex: 1 }}><DatePicker style={{ width: '100%' }} /></Form.Item>
          </Space>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="deposit_amount" label="保证金（元）" style={{ flex: 1 }}><InputNumber style={{ width: '100%' }} min={0} step={10000} /></Form.Item>
            <Form.Item name="deposit_due" label="保证金应退日" style={{ flex: 1 }}><DatePicker style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="status" label="状态" style={{ flex: 1 }}><Select options={statusOptions} /></Form.Item>
          </Space>
          {editing && (
            <Space size="large" style={{ display: 'flex' }}>
              <Form.Item name="win_amount" label="中标金额（元）" style={{ flex: 1 }}><InputNumber style={{ width: '100%' }} min={0} step={10000} /></Form.Item>
              <Form.Item name="deposit_returned" label="保证金状态" style={{ flex: 1 }}>
                <Select options={[{ value: true, label: '已退' }, { value: false, label: '未退' }]} />
              </Form.Item>
            </Space>
          )}
          <Form.Item name="fail_reason" label="废标/未中标原因"><Input /></Form.Item>
          <Form.Item name="competitor_info" label="竞品信息"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="remark" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
