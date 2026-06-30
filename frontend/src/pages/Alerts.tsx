import { useEffect, useState, useCallback } from 'react'
import {
  Table, Tag, Space, Select, Button, Modal, Form, Input, message,
} from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import http, { downloadCsv } from '../api/client'
import type { ApiResponse, PageResult, Alert } from '../api/types'
import { ALERT_LEVEL, ALERT_STATUS, ALERT_SOURCE } from '../constants'

const sourceOptions = Object.entries(ALERT_SOURCE).map(([v, l]) => ({ value: v, label: l }))
const levelOptions = Object.entries(ALERT_LEVEL).map(([v, o]) => ({ value: v, label: o.label }))
const statusOptions = Object.entries(ALERT_STATUS).map(([v, o]) => ({ value: v, label: o.label }))

export default function Alerts() {
  const [rows, setRows] = useState<Alert[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [source, setSource] = useState<string | undefined>()
  const [level, setLevel] = useState<string | undefined>()
  const [status, setStatus] = useState<string | undefined>()
  const [handling, setHandling] = useState<Alert | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(() => {
    setLoading(true)
    http
      .get<ApiResponse<PageResult<Alert>>>('/alerts', {
        params: { source, level, status, page, page_size: 10 },
      })
      .then(({ data }) => {
        setRows(data.data.items)
        setTotal(data.data.total)
      })
      .finally(() => setLoading(false))
  }, [source, level, status, page])

  useEffect(() => { load() }, [load])

  const openHandle = (row: Alert) => {
    setHandling(row)
    form.setFieldsValue({ status: row.status === 'pending' ? 'processing' : row.status, handle_remark: row.handle_remark })
  }

  const submitHandle = async () => {
    const v = await form.validateFields()
    await http.post(`/alerts/${handling!.id}/handle`, v)
    message.success('已更新预警状态')
    setHandling(null)
    load()
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Select placeholder="来源" allowClear options={sourceOptions} value={source}
          onChange={(v) => { setSource(v); setPage(1) }} style={{ width: 120 }} />
        <Select placeholder="等级" allowClear options={levelOptions} value={level}
          onChange={(v) => { setLevel(v); setPage(1) }} style={{ width: 120 }} />
        <Select placeholder="状态" allowClear options={statusOptions} value={status}
          onChange={(v) => { setStatus(v); setPage(1) }} style={{ width: 120 }} />
        <Button type="primary" icon={<SearchOutlined />} onClick={() => { setPage(1); load() }}>查询</Button>
        <Button onClick={() => downloadCsv('/export/alerts', 'alerts.csv', { source })}>导出 CSV</Button>
      </Space>

      <Table
        scroll={{ x: 'max-content' }}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={{ current: page, pageSize: 10, total, onChange: setPage }}
        columns={[
          { title: '#', dataIndex: 'id', width: 60 },
          { title: '预警标题', dataIndex: 'title', ellipsis: true },
          { title: '来源', dataIndex: 'source', width: 80, render: (s) => <Tag>{ALERT_SOURCE[s] || s}</Tag> },
          { title: '关联项目', dataIndex: ['project', 'name'], width: 180, render: (v) => v || '-' },
          {
            title: '等级', dataIndex: 'level', width: 90,
            render: (l) => <Tag color={ALERT_LEVEL[l]?.color}>{ALERT_LEVEL[l]?.label || l}</Tag>,
          },
          { title: '责任人', dataIndex: ['owner', 'name'], width: 90, render: (v) => v || '-' },
          { title: '截止日期', dataIndex: 'due_date', width: 110, render: (v) => v || '-' },
          {
            title: '状态', dataIndex: 'status', width: 90,
            render: (s) => <Tag color={ALERT_STATUS[s]?.color}>{ALERT_STATUS[s]?.label || s}</Tag>,
          },
          {
            title: '操作', width: 80, fixed: 'right',
            render: (_, r) => <a onClick={() => openHandle(r)}>处理</a>,
          },
        ]}
      />

      <Modal title="处理预警" open={!!handling} onOk={submitHandle} onCancel={() => setHandling(null)} destroyOnClose>
        <div style={{ marginBottom: 12, color: '#555' }}>{handling?.title}</div>
        <Form form={form} layout="vertical">
          <Form.Item name="status" label="处理结果" rules={[{ required: true }]}>
            <Select options={statusOptions} />
          </Form.Item>
          <Form.Item name="handle_remark" label="处理说明">
            <Input.TextArea rows={3} placeholder="记录处理过程与结论，关闭预警将留痕" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
