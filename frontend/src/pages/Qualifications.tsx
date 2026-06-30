import { useEffect, useState, useCallback } from 'react'
import {
  Table, Tag, Space, Input, Select, Button, Modal, Form, DatePicker, message,
  Popconfirm, Tooltip, Timeline, Empty, Alert as AntAlert,
} from 'antd'
import { PlusOutlined, SearchOutlined, SafetyCertificateOutlined, SyncOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import http from '../api/client'
import type { ApiResponse, PageResult, Qualification, VerifyRecord, ScanResult } from '../api/types'
import { QUAL_STATUS, VERIFY_STATUS, SECRET_LEVEL } from '../constants'
import { useAuth } from '../auth/AuthContext'

const statusOptions = Object.entries(QUAL_STATUS).map(([v, o]) => ({ value: v, label: o.label }))
const verifyOptions = Object.entries(VERIFY_STATUS).map(([v, o]) => ({ value: v, label: o.label }))
const secretOptions = Object.entries(SECRET_LEVEL).map(([v, o]) => ({ value: v, label: o.label }))

function expireTag(days?: number | null) {
  if (days === null || days === undefined) return <span style={{ color: '#999' }}>-</span>
  if (days < 0) return <Tag color="red">已过期 {Math.abs(days)} 天</Tag>
  if (days <= 30) return <Tag color="red">{days} 天</Tag>
  if (days <= 90) return <Tag color="orange">{days} 天</Tag>
  return <span>{days} 天</span>
}

export default function Qualifications() {
  const { has } = useAuth()
  const [rows, setRows] = useState<Qualification[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState<string | undefined>()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Qualification | null>(null)
  const [verifyTarget, setVerifyTarget] = useState<Qualification | null>(null)
  const [records, setRecords] = useState<VerifyRecord[]>([])
  const [form] = Form.useForm()
  const [verifyForm] = Form.useForm()

  const load = useCallback(() => {
    setLoading(true)
    http
      .get<ApiResponse<PageResult<Qualification>>>('/qualifications', {
        params: { keyword: keyword || undefined, status, page, page_size: 10 },
      })
      .then(({ data }) => { setRows(data.data.items); setTotal(data.data.total) })
      .finally(() => setLoading(false))
  }, [keyword, status, page])

  useEffect(() => { load() }, [load])

  const canManage = has('qualification:manage')

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ status: 'valid', secret_level: 'internal' })
    setModalOpen(true)
  }

  const openEdit = (row: Qualification) => {
    setEditing(row)
    form.setFieldsValue({
      ...row,
      valid_from: row.valid_from ? dayjs(row.valid_from) : undefined,
      valid_to: row.valid_to ? dayjs(row.valid_to) : undefined,
      annual_review_date: row.annual_review_date ? dayjs(row.annual_review_date) : undefined,
    })
    setModalOpen(true)
  }

  const submit = async () => {
    const v = await form.validateFields()
    const payload = {
      ...v,
      valid_from: v.valid_from ? v.valid_from.format('YYYY-MM-DD') : undefined,
      valid_to: v.valid_to ? v.valid_to.format('YYYY-MM-DD') : undefined,
      annual_review_date: v.annual_review_date ? v.annual_review_date.format('YYYY-MM-DD') : undefined,
    }
    try {
      if (editing) {
        await http.put(`/qualifications/${editing.id}`, payload)
        message.success('已更新')
      } else {
        await http.post('/qualifications', payload)
        message.success('已创建')
      }
      setModalOpen(false)
      load()
    } catch { /* 拦截器提示 */ }
  }

  const remove = async (id: number) => {
    await http.delete(`/qualifications/${id}`)
    message.success('已删除')
    load()
  }

  const openVerify = async (row: Qualification) => {
    setVerifyTarget(row)
    verifyForm.resetFields()
    verifyForm.setFieldsValue({ result: 'verified', method: '官网核验' })
    const { data } = await http.get<ApiResponse<VerifyRecord[]>>(`/qualifications/${row.id}/verify-records`)
    setRecords(data.data)
  }

  const submitVerify = async () => {
    const v = await verifyForm.validateFields()
    await http.post(`/qualifications/${verifyTarget!.id}/verify`, v)
    message.success('核验记录已保存')
    setVerifyTarget(null)
    load()
  }

  const scan = async () => {
    const { data } = await http.post<ApiResponse<ScanResult>>('/qualifications/scan')
    const r = data.data
    Modal.success({
      title: '到期扫描完成',
      content: (
        <div>
          <p>共扫描 {r.scanned} 项资质。</p>
          <p>即将到期（90 天内）：<b style={{ color: '#fa8c16' }}>{r.expiring}</b> 项</p>
          <p>已过期：<b style={{ color: '#f5222d' }}>{r.expired}</b> 项</p>
          <p>已生成预警：<b>{r.alerts_created}</b> 条（可在预警中心查看处理）</p>
        </div>
      ),
    })
    load()
  }

  return (
    <div>
      <AntAlert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="资质到期前 90 天内标记『即将到期』、过期标记『已过期』，点击「扫描到期」可一键刷新状态并向预警中心推送预警（规则 R-001）。"
      />
      <Space style={{ marginBottom: 16 }} wrap>
        <Input
          placeholder="资质名称/证书编号"
          prefix={<SearchOutlined />}
          allowClear
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onPressEnter={() => { setPage(1); load() }}
          style={{ width: 220 }}
        />
        <Select placeholder="状态" allowClear options={statusOptions} value={status}
          onChange={(v) => { setStatus(v); setPage(1) }} style={{ width: 140 }} />
        <Button type="primary" icon={<SearchOutlined />} onClick={() => { setPage(1); load() }}>查询</Button>
        {canManage && (
          <>
            <Button icon={<PlusOutlined />} type="primary" ghost onClick={openCreate}>新增资质</Button>
            <Button icon={<SyncOutlined />} onClick={scan}>扫描到期</Button>
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
            title: '资质名称',
            dataIndex: 'name',
            render: (t, r) => (
              <span>
                <SafetyCertificateOutlined style={{ color: '#1f6feb', marginRight: 6 }} />
                {t}
                {r.secret_level === 'classified' && <Tag color="red" style={{ marginLeft: 6 }}>涉密</Tag>}
              </span>
            ),
          },
          { title: '等级', dataIndex: 'level', width: 80, render: (v) => v || '-' },
          { title: '证书编号', dataIndex: 'cert_no', width: 160, render: (v) => v || '-' },
          { title: '有效期至', dataIndex: 'valid_to', width: 110, render: (v) => v || '-' },
          { title: '距到期', dataIndex: 'days_to_expire', width: 110, render: expireTag },
          {
            title: '核验',
            dataIndex: 'verify_status',
            width: 100,
            render: (s) => <Tag color={VERIFY_STATUS[s]?.color}>{VERIFY_STATUS[s]?.label || s}</Tag>,
          },
          {
            title: '状态',
            dataIndex: 'status',
            width: 100,
            render: (s) => <Tag color={QUAL_STATUS[s]?.color}>{QUAL_STATUS[s]?.label || s}</Tag>,
          },
          {
            title: '操作',
            width: 160,
            fixed: 'right',
            render: (_, r) =>
              canManage ? (
                <Space>
                  <a onClick={() => openVerify(r)}>核验</a>
                  <a onClick={() => openEdit(r)}>编辑</a>
                  <Popconfirm title="确认删除该资质？" onConfirm={() => remove(r.id)}>
                    <a style={{ color: '#f5222d' }}>删除</a>
                  </Popconfirm>
                </Space>
              ) : (
                <Tooltip title="无维护权限">-</Tooltip>
              ),
          },
        ]}
      />

      <Modal
        title={editing ? '编辑资质' : '新增资质'}
        open={modalOpen}
        onOk={submit}
        onCancel={() => setModalOpen(false)}
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="资质名称" rules={[{ required: true, message: '请输入资质名称' }]}>
            <Input />
          </Form.Item>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="type" label="资质类型" style={{ flex: 1 }}><Input placeholder="施工总承包/专业承包/许可证" /></Form.Item>
            <Form.Item name="level" label="等级" style={{ flex: 1 }}><Input placeholder="一级/二级" /></Form.Item>
          </Space>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="cert_no" label="证书编号" style={{ flex: 1 }}><Input /></Form.Item>
            <Form.Item name="issuing_authority" label="发证机关" style={{ flex: 1 }}><Input /></Form.Item>
          </Space>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="valid_from" label="有效期起" style={{ flex: 1 }}><DatePicker style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="valid_to" label="有效期至" style={{ flex: 1 }}><DatePicker style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="annual_review_date" label="年审日期" style={{ flex: 1 }}><DatePicker style={{ width: '100%' }} /></Form.Item>
          </Space>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="status" label="状态" style={{ flex: 1 }}><Select options={statusOptions} /></Form.Item>
            <Form.Item name="secret_level" label="密级" style={{ flex: 1 }}><Select options={secretOptions} /></Form.Item>
          </Space>
          <Form.Item name="scope" label="承接范围"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="region_limit" label="地域限制"><Input /></Form.Item>
          <Form.Item name="remark" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`核验 - ${verifyTarget?.name || ''}`}
        open={!!verifyTarget}
        onOk={submitVerify}
        onCancel={() => setVerifyTarget(null)}
        width={560}
        destroyOnClose
      >
        <Form form={verifyForm} layout="vertical">
          <Form.Item name="result" label="核验结果" rules={[{ required: true }]}>
            <Select options={verifyOptions} />
          </Form.Item>
          <Form.Item name="method" label="核验方式"><Input placeholder="官网核验/人工核验" /></Form.Item>
          <Form.Item name="remark" label="核验说明"><Input.TextArea rows={2} /></Form.Item>
        </Form>
        <div style={{ fontWeight: 600, margin: '8px 0' }}>历史核验记录</div>
        {records.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无核验记录" />
        ) : (
          <Timeline
            items={records.map((r) => ({
              color: VERIFY_STATUS[r.result]?.color === 'success' ? 'green' : r.result === 'failed' ? 'red' : 'blue',
              children: (
                <div>
                  <Tag color={VERIFY_STATUS[r.result]?.color}>{VERIFY_STATUS[r.result]?.label}</Tag>
                  {r.method && <span style={{ marginLeft: 4 }}>{r.method}</span>}
                  <div style={{ color: '#888', fontSize: 12 }}>
                    {r.operator_name} · {new Date(r.created_at).toLocaleString('zh-CN')}
                  </div>
                  {r.remark && <div style={{ fontSize: 13 }}>{r.remark}</div>}
                </div>
              ),
            }))}
          />
        )}
      </Modal>
    </div>
  )
}
