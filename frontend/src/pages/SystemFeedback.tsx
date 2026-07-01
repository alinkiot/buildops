import { useEffect, useState } from 'react'
import { Button, Table, Tag, Select, message, Modal } from 'antd'
import { useNavigate } from 'react-router-dom'
import http from '../api/client'
import type { ApiResponse, PageResult, Feedback } from '../api/types'

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending: { label: '待确认', color: 'default' },
  processing: { label: '处理中', color: 'processing' },
  ignored: { label: '不处理', color: 'warning' },
  resolved: { label: '已解决', color: 'success' },
}

const STATUS_OPTIONS = Object.entries(STATUS_MAP).map(([value, { label }]) => ({ value, label }))

export default function SystemFeedback() {
  const [rows, setRows] = useState<Feedback[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [detailItem, setDetailItem] = useState<Feedback | null>(null)
  const navigate = useNavigate()

  const fetchData = (p: number) => {
    setLoading(true)
    http.get<ApiResponse<PageResult<Feedback>>>('/feedback', { params: { page: p, page_size: 15 } })
      .then(({ data }) => { setRows(data.data.items); setTotal(data.data.total) })
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchData(page) }, [page])

  const handleStatusChange = async (id: number, status: string) => {
    try {
      await http.put(`/feedback/${id}/status`, { status })
      message.success('状态更新成功')
      fetchData(page)
    } catch {
      // error handled by interceptor
    }
  }

  return (
    <>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={{ current: page, pageSize: 15, total, onChange: (p) => setPage(p) }}
        columns={[
        {
          title: '提交时间',
          dataIndex: 'created_at',
          width: 170,
          render: (v) => (v ? new Date(v).toLocaleString('zh-CN') : '-'),
        },
        {
          title: '标题',
          dataIndex: 'title',
          ellipsis: true,
        },
        {
          title: '描述',
          dataIndex: 'description',
          ellipsis: true,
          render: (v: string | undefined) => {
            if (!v) return '-'
            return v.length > 250 ? v.slice(0, 250) + '...' : v
          },
        },
        {
          title: '来源页面',
          dataIndex: 'page_url',
          width: 160,
          ellipsis: true,
          render: (v) => v ? (
            <a onClick={() => navigate(v)} style={{ cursor: 'pointer' }}>{v}</a>
          ) : '-',
        },
        {
          title: '状态',
          dataIndex: 'status',
          width: 130,
          render: (status: string, record: Feedback) => (
            <Select
              size="small"
              value={status}
              options={STATUS_OPTIONS}
              onChange={(val) => handleStatusChange(record.id, val)}
              style={{ width: 100 }}
              optionRender={(option) => {
                const s = STATUS_MAP[option.value as string]
                return s ? <Tag color={s.color}>{s.label}</Tag> : option.label
              }}
            />
          ),
        },
        {
          title: '操作',
          key: 'action',
          width: 80,
          render: (_: unknown, record: Feedback) => (
            <Button type="link" size="small" onClick={() => setDetailItem(record)}>
              详情
            </Button>
          ),
        },
      ]}
      />

      {/* Detail Modal */}
      <Modal
        title="意见反馈"
        open={!!detailItem}
        onCancel={() => setDetailItem(null)}
        footer={null}
        width={560}
      >
        {detailItem && (
          <div style={{ lineHeight: 1.8 }}>
            <p><strong>标题：</strong>{detailItem.title}</p>
            <p><strong>描述：</strong></p>
            <div style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: 12, borderRadius: 6, maxHeight: 400, overflow: 'auto' }}>
              {detailItem.description || '无'}
            </div>
            <p style={{ marginTop: 12 }}><strong>来源页面：</strong>{detailItem.page_url || '-'}</p>
            <p><strong>状态：</strong><Tag color={STATUS_MAP[detailItem.status]?.color}>{STATUS_MAP[detailItem.status]?.label}</Tag></p>
            <p><strong>提交时间：</strong>{detailItem.created_at ? new Date(detailItem.created_at).toLocaleString('zh-CN') : '-'}</p>
          </div>
        )}
      </Modal>
    </>
  )
}
