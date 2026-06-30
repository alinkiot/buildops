import { useEffect, useState, useCallback } from 'react'
import {
  Table, Tag, Space, Input, Select, Button, Upload, message, Popconfirm,
} from 'antd'
import { UploadOutlined, DownloadOutlined, SearchOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'
import http, { tokenStore } from '../api/client'
import type { ApiResponse, PageResult, FileObject } from '../api/types'
import { SECRET_LEVEL, FILE_STATUS } from '../constants'
import { useAuth } from '../auth/AuthContext'

const secretOptions = Object.entries(SECRET_LEVEL).map(([v, o]) => ({ value: v, label: o.label }))

const fmtSize = (n: number) => {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}

export default function Files() {
  const { has } = useAuth()
  const [rows, setRows] = useState<FileObject[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [secret, setSecret] = useState<string | undefined>()

  const load = useCallback(() => {
    setLoading(true)
    http
      .get<ApiResponse<PageResult<FileObject>>>('/files', {
        params: { keyword: keyword || undefined, secret_level: secret, page, page_size: 10 },
      })
      .then(({ data }) => {
        setRows(data.data.items)
        setTotal(data.data.total)
      })
      .finally(() => setLoading(false))
  }, [keyword, secret, page])

  useEffect(() => { load() }, [load])

  const canManage = has('file:manage')

  const uploadProps: UploadProps = {
    name: 'file',
    action: '/api/files/upload',
    headers: { Authorization: `Bearer ${tokenStore.get()}` },
    data: { secret_level: 'internal' },
    showUploadList: false,
    onChange(info) {
      if (info.file.status === 'done') {
        message.success(`${info.file.name} 上传成功`)
        load()
      } else if (info.file.status === 'error') {
        message.error(`${info.file.name} 上传失败`)
      }
    },
  }

  const download = async (row: FileObject) => {
    try {
      const resp = await http.get(`/files/${row.id}/download`, { responseType: 'blob' })
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      a.download = row.name
      a.click()
      URL.revokeObjectURL(url)
    } catch { /* 拦截器提示 */ }
  }

  const preview = async (row: FileObject) => {
    try {
      const resp = await http.get(`/files/${row.id}/preview`, { responseType: 'blob' })
      const url = URL.createObjectURL(resp.data)
      window.open(url, '_blank')
      // 延迟释放，确保新标签页已加载
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch { /* 拦截器提示（如 415 不支持预览） */ }
  }

  const changeSecret = async (row: FileObject, level: string) => {
    await http.put(`/files/${row.id}`, { secret_level: level })
    message.success('密级已更新')
    load()
  }

  const remove = async (id: number) => {
    await http.delete(`/files/${id}`)
    message.success('已删除')
    load()
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Input
          placeholder="文件名"
          prefix={<SearchOutlined />}
          allowClear
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onPressEnter={() => { setPage(1); load() }}
          style={{ width: 200 }}
        />
        <Select
          placeholder="密级"
          allowClear
          options={secretOptions}
          value={secret}
          onChange={(v) => { setSecret(v); setPage(1) }}
          style={{ width: 120 }}
        />
        <Button type="primary" icon={<SearchOutlined />} onClick={() => { setPage(1); load() }}>查询</Button>
        {canManage && (
          <Upload {...uploadProps}>
            <Button icon={<UploadOutlined />} type="primary" ghost>上传文件</Button>
          </Upload>
        )}
      </Space>

      <Table
        scroll={{ x: 'max-content' }}
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={{ current: page, pageSize: 10, total, onChange: setPage }}
        columns={[
          { title: '文件名', dataIndex: 'name', ellipsis: true },
          { title: '业务类型', dataIndex: 'business_type', width: 110, render: (v) => v || '-' },
          { title: '版本', dataIndex: 'version', width: 70, render: (v) => `v${v}` },
          { title: '大小', dataIndex: 'size', width: 100, render: fmtSize },
          {
            title: '密级',
            dataIndex: 'secret_level',
            width: 130,
            render: (s, r) =>
              canManage ? (
                <Select
                  size="small"
                  variant="borderless"
                  value={s}
                  options={secretOptions}
                  onChange={(v) => changeSecret(r, v)}
                  style={{ width: 100 }}
                />
              ) : (
                <Tag color={SECRET_LEVEL[s]?.color}>{SECRET_LEVEL[s]?.label}</Tag>
              ),
          },
          { title: '下载次数', dataIndex: 'download_count', width: 90 },
          {
            title: '状态',
            dataIndex: 'status',
            width: 80,
            render: (s) => <Tag color={FILE_STATUS[s]?.color}>{FILE_STATUS[s]?.label || s}</Tag>,
          },
          {
            title: '操作',
            width: 130,
            fixed: 'right',
            render: (_, r) => (
              <Space>
                <a onClick={() => preview(r)}>预览</a>
                <a onClick={() => download(r)}><DownloadOutlined /> 下载</a>
                {canManage && (
                  <Popconfirm title="确认删除？" onConfirm={() => remove(r.id)}>
                    <a style={{ color: '#f5222d' }}>删除</a>
                  </Popconfirm>
                )}
              </Space>
            ),
          },
        ]}
      />
    </div>
  )
}
