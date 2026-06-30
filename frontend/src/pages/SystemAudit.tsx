import { useEffect, useState } from 'react'
import { Table, Tag } from 'antd'
import http from '../api/client'
import type { ApiResponse, PageResult } from '../api/types'

interface AuditRow {
  id: number; username?: string; action: string; target_type?: string; target_id?: string; ip?: string; created_at?: string
}

export default function SystemAudit() {
  const [rows, setRows] = useState<AuditRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    http.get<ApiResponse<PageResult<AuditRow>>>('/system/audit-logs', { params: { page, page_size: 15 } })
      .then(({ data }) => { setRows(data.data.items); setTotal(data.data.total) })
      .finally(() => setLoading(false))
  }, [page])

  return (
    <Table
      rowKey="id" loading={loading} dataSource={rows}
      pagination={{ current: page, pageSize: 15, total, onChange: setPage }}
      columns={[
        { title: '时间', dataIndex: 'created_at', render: (v) => (v ? new Date(v).toLocaleString('zh-CN') : '-') },
        { title: '操作人', dataIndex: 'username', render: (v) => v || '-' },
        { title: '动作', dataIndex: 'action', render: (v) => <Tag>{v}</Tag> },
        { title: '对象类型', dataIndex: 'target_type', render: (v) => v || '-' },
        { title: '对象ID', dataIndex: 'target_id', render: (v) => v || '-' },
        { title: 'IP', dataIndex: 'ip', render: (v) => v || '-' },
      ]}
    />
  )
}
