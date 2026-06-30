import { useEffect, useState, useCallback } from 'react'
import {
  Button, Table, Tag, Space, Input, Select, Modal, Form, InputNumber, DatePicker,
  message, Popconfirm, Drawer, Descriptions,
} from 'antd'
import { PlusOutlined, SearchOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import http, { downloadCsv } from '../api/client'
import type { ApiResponse, PageResult, Project } from '../api/types'
import { PROJECT_STATUS, SECRET_LEVEL, fmtMoney } from '../constants'
import { useAuth } from '../auth/AuthContext'

const statusOptions = Object.entries(PROJECT_STATUS).map(([v, o]) => ({ value: v, label: o.label }))
const secretOptions = Object.entries(SECRET_LEVEL).map(([v, o]) => ({ value: v, label: o.label }))

export default function Projects() {
  const { has } = useAuth()
  const [rows, setRows] = useState<Project[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState<string | undefined>()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Project | null>(null)
  const [detail, setDetail] = useState<Project | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(() => {
    setLoading(true)
    http
      .get<ApiResponse<PageResult<Project>>>('/projects', {
        params: { keyword: keyword || undefined, status, page, page_size: 10 },
      })
      .then(({ data }) => {
        setRows(data.data.items)
        setTotal(data.data.total)
      })
      .finally(() => setLoading(false))
  }, [keyword, status, page])

  useEffect(() => { load() }, [load])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ status: 'preparing', secret_level: 'internal', contract_amount: 0 })
    setModalOpen(true)
  }

  const openEdit = (row: Project) => {
    setEditing(row)
    form.setFieldsValue({
      ...row,
      contract_amount: parseFloat(row.contract_amount),
      start_date: row.start_date ? dayjs(row.start_date) : undefined,
      plan_end_date: row.plan_end_date ? dayjs(row.plan_end_date) : undefined,
    })
    setModalOpen(true)
  }

  const submit = async () => {
    const v = await form.validateFields()
    const payload = {
      ...v,
      contract_amount: String(v.contract_amount ?? 0),
      start_date: v.start_date ? v.start_date.format('YYYY-MM-DD') : undefined,
      plan_end_date: v.plan_end_date ? v.plan_end_date.format('YYYY-MM-DD') : undefined,
    }
    try {
      if (editing) {
        await http.put(`/projects/${editing.id}`, payload)
        message.success('已更新')
      } else {
        await http.post('/projects', payload)
        message.success('已创建')
      }
      setModalOpen(false)
      load()
    } catch { /* 拦截器提示 */ }
  }

  const remove = async (id: number) => {
    await http.delete(`/projects/${id}`)
    message.success('已删除')
    load()
  }

  const canManage = has('project:manage')

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Input
          placeholder="项目名称/编号"
          prefix={<SearchOutlined />}
          allowClear
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onPressEnter={() => { setPage(1); load() }}
          style={{ width: 200 }}
        />
        <Select
          placeholder="项目状态"
          allowClear
          options={statusOptions}
          value={status}
          onChange={(v) => { setStatus(v); setPage(1) }}
          style={{ width: 140 }}
        />
        <Button type="primary" icon={<SearchOutlined />} onClick={() => { setPage(1); load() }}>
          查询
        </Button>
        {canManage && (
          <Button icon={<PlusOutlined />} type="primary" ghost onClick={openCreate}>
            新增项目
          </Button>
        )}
        <Button onClick={() => downloadCsv('/export/projects', 'projects.csv')}>导出 CSV</Button>
      </Space>

      <Table
        scroll={{ x: 'max-content' }}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={{ current: page, pageSize: 10, total, onChange: setPage }}
        columns={[
          { title: '编号', dataIndex: 'code', width: 130 },
          {
            title: '项目名称',
            dataIndex: 'name',
            render: (t, r) => (
              <a onClick={() => setDetail(r)}>
                {t}
                {r.secret_level === 'classified' && <Tag color="red" style={{ marginLeft: 6 }}>涉密</Tag>}
              </a>
            ),
          },
          { title: '甲方', dataIndex: ['client', 'name'], width: 180, render: (v) => v || '-' },
          { title: '负责人', dataIndex: ['owner', 'name'], width: 90, render: (v) => v || '-' },
          { title: '合同额', dataIndex: 'contract_amount', width: 110, render: fmtMoney },
          { title: '待回款', width: 110, render: (_, r) => fmtMoney(parseFloat(r.contract_amount) - parseFloat(r.received_amount)) },
          {
            title: '状态',
            dataIndex: 'status',
            width: 90,
            render: (s) => <Tag color={PROJECT_STATUS[s]?.color}>{PROJECT_STATUS[s]?.label || s}</Tag>,
          },
          {
            title: '操作',
            width: 130,
            fixed: 'right',
            render: (_, r) =>
              canManage ? (
                <Space>
                  <a onClick={() => openEdit(r)}>编辑</a>
                  <Popconfirm title="确认删除该项目？" onConfirm={() => remove(r.id)}>
                    <a style={{ color: '#f5222d' }}>删除</a>
                  </Popconfirm>
                </Space>
              ) : (
                <a onClick={() => setDetail(r)}>查看</a>
              ),
          },
        ]}
      />

      <Modal
        title={editing ? '编辑项目' : '新增项目'}
        open={modalOpen}
        onOk={submit}
        onCancel={() => setModalOpen(false)}
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="code" label="项目编号" rules={[{ required: true, message: '请输入项目编号' }]}>
            <Input disabled={!!editing} placeholder="如 PRJ-2024-001" />
          </Form.Item>
          <Form.Item name="name" label="项目名称" rules={[{ required: true, message: '请输入项目名称' }]}>
            <Input />
          </Form.Item>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="type" label="项目类型" style={{ flex: 1 }}>
              <Input placeholder="市政/房建/装修" />
            </Form.Item>
            <Form.Item name="region" label="地域" style={{ flex: 1 }}>
              <Input />
            </Form.Item>
          </Space>
          <Form.Item name="contract_amount" label="合同金额（元）" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} min={0} step={10000} />
          </Form.Item>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="start_date" label="开工日期" style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="plan_end_date" label="计划竣工" style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Space>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="status" label="项目状态" style={{ flex: 1 }}>
              <Select options={statusOptions} />
            </Form.Item>
            <Form.Item name="secret_level" label="密级" style={{ flex: 1 }}>
              <Select options={secretOptions} />
            </Form.Item>
          </Space>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer title="项目详情" open={!!detail} onClose={() => setDetail(null)} width={520}>
        {detail && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="项目编号">{detail.code}</Descriptions.Item>
            <Descriptions.Item label="项目名称">{detail.name}</Descriptions.Item>
            <Descriptions.Item label="类型/地域">{[detail.type, detail.region].filter(Boolean).join(' / ') || '-'}</Descriptions.Item>
            <Descriptions.Item label="甲方">{detail.client?.name || '-'}</Descriptions.Item>
            <Descriptions.Item label="负责人">{detail.owner?.name || '-'}</Descriptions.Item>
            <Descriptions.Item label="合同额">{fmtMoney(detail.contract_amount)}</Descriptions.Item>
            <Descriptions.Item label="已回款">{fmtMoney(detail.received_amount)}</Descriptions.Item>
            <Descriptions.Item label="成本">{fmtMoney(detail.cost_amount)}</Descriptions.Item>
            <Descriptions.Item label="工期">
              {[detail.start_date, detail.plan_end_date].filter(Boolean).join(' ~ ') || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={PROJECT_STATUS[detail.status]?.color}>{PROJECT_STATUS[detail.status]?.label}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="密级">
              <Tag color={SECRET_LEVEL[detail.secret_level]?.color}>{SECRET_LEVEL[detail.secret_level]?.label}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="备注">{detail.remark || '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  )
}
