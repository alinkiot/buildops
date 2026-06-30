import { useEffect, useState, useCallback } from 'react'
import {
  Table, Tag, Space, Select, Button, Modal, Form, Input, message, Upload,
  Row, Col, Card, Progress, Statistic, Popconfirm, Switch, Empty, Tooltip,
} from 'antd'
import {
  UploadOutlined, SyncOutlined, InboxOutlined, PlusOutlined, AuditOutlined,
} from '@ant-design/icons'
import http, { tokenStore } from '../api/client'
import type { ApiResponse, PageResult, Project, DocItem, DocTemplate, Completeness, DocScanResult } from '../api/types'
import { DOC_STATUS } from '../constants'
import { useAuth } from '../auth/AuthContext'

const statusOptions = Object.entries(DOC_STATUS).map(([v, o]) => ({ value: v, label: o.label }))

export default function Documents() {
  const { has } = useAuth()
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState<number | undefined>()
  const [rows, setRows] = useState<DocItem[]>([])
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string | undefined>()
  const [comp, setComp] = useState<Completeness | null>(null)
  const [reviewTarget, setReviewTarget] = useState<DocItem | null>(null)
  const [addOpen, setAddOpen] = useState(false)
  const [tplOpen, setTplOpen] = useState(false)
  const [templates, setTemplates] = useState<DocTemplate[]>([])
  const [reviewForm] = Form.useForm()
  const [addForm] = Form.useForm()

  const canManage = has('document:manage')
  const canReview = has('document:review')

  useEffect(() => {
    http.get<ApiResponse<PageResult<Project>>>('/projects', { params: { page_size: 100 } }).then(({ data }) => {
      setProjects(data.data.items)
      if (data.data.items.length) setProjectId(data.data.items[0].id)
    })
  }, [])

  const loadItems = useCallback(() => {
    if (!projectId) return
    setLoading(true)
    http.get<ApiResponse<PageResult<DocItem>>>('/documents', { params: { project_id: projectId, status } })
      .then(({ data }) => setRows(data.data.items))
      .finally(() => setLoading(false))
    http.get<ApiResponse<Completeness>>('/documents/completeness', { params: { project_id: projectId } })
      .then(({ data }) => setComp(data.data))
  }, [projectId, status])

  useEffect(() => { loadItems() }, [loadItems])

  const openReview = (item: DocItem) => {
    setReviewTarget(item)
    reviewForm.setFieldsValue({ approved: true, review_remark: '' })
  }
  const submitReview = async () => {
    const v = await reviewForm.validateFields()
    await http.post(`/documents/${reviewTarget!.id}/review`, v)
    message.success('审核完成')
    setReviewTarget(null)
    loadItems()
  }

  const addItem = async () => {
    const v = await addForm.validateFields()
    await http.post('/documents', { ...v, project_id: projectId })
    message.success('已新增资料条目')
    setAddOpen(false)
    addForm.resetFields()
    loadItems()
  }

  const openTemplates = async () => {
    const { data } = await http.get<ApiResponse<DocTemplate[]>>('/documents/templates')
    setTemplates(data.data)
    setTplOpen(true)
  }
  const applyTemplate = async () => {
    const { data } = await http.post<ApiResponse<{ created: number }>>('/documents/apply-template', { project_id: projectId })
    message.success(`已生成 ${data.data.created} 条资料条目`)
    setTplOpen(false)
    loadItems()
  }

  const scan = async () => {
    const { data } = await http.post<ApiResponse<DocScanResult>>('/documents/scan', null, { params: { project_id: projectId } })
    const r = data.data
    Modal.warning({
      title: '缺项扫描完成',
      content: `扫描 ${r.scanned} 项，新增缺项 ${r.missing} 项，生成预警 ${r.alerts_created} 条（已推送预警中心）。`,
    })
    loadItems()
  }

  const archive = async () => {
    const { data } = await http.post<ApiResponse<{ archived: number }>>('/documents/archive', null, { params: { project_id: projectId } })
    message.success(`组卷完成，已归档 ${data.data.archived} 份已通过资料`)
    loadItems()
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
          placeholder="请选择项目"
          showSearch
          optionFilterProp="label"
        />
        <Select placeholder="状态" allowClear options={statusOptions} value={status}
          onChange={setStatus} style={{ width: 130 }} />
        {canManage && projectId && (
          <>
            <Button icon={<InboxOutlined />} onClick={openTemplates}>套用模板</Button>
            <Button icon={<PlusOutlined />} onClick={() => setAddOpen(true)}>新增条目</Button>
            <Button icon={<SyncOutlined />} onClick={scan}>缺项扫描</Button>
            <Popconfirm title="将已通过资料归档组卷？" onConfirm={archive}>
              <Button icon={<AuditOutlined />}>竣工组卷</Button>
            </Popconfirm>
          </>
        )}
      </Space>

      {comp && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={8} lg={6}>
            <Card size="small">
              <div style={{ marginBottom: 4 }}>资料完整度（必需项）</div>
              <Progress
                percent={comp.completeness}
                status={comp.completeness >= 100 ? 'success' : comp.missing > 0 ? 'exception' : 'active'}
              />
              <div style={{ color: '#999', fontSize: 12 }}>
                已通过必需项 {comp.approved} / 必需 {comp.required_total}
              </div>
            </Card>
          </Col>
          <Col xs={12} sm={4} lg={4}><Card size="small"><Statistic title="资料总数" value={comp.total} /></Card></Col>
          <Col xs={12} sm={4} lg={4}><Card size="small"><Statistic title="待审核" value={comp.pending_review} valueStyle={{ color: '#1677ff' }} /></Card></Col>
          <Col xs={12} sm={4} lg={4}><Card size="small"><Statistic title="待上传" value={comp.pending_upload} /></Card></Col>
          <Col xs={12} sm={4} lg={4}><Card size="small"><Statistic title="缺项" value={comp.missing} valueStyle={{ color: '#f5222d' }} /></Card></Col>
        </Row>
      )}

      {!projectId ? (
        <Empty description="请选择项目" />
      ) : (
        <Table
          scroll={{ x: 'max-content' }}
          rowKey="id"
          loading={loading}
          dataSource={rows}
          pagination={false}
          columns={[
            { title: '资料名称', dataIndex: 'name', render: (t, r) => (
              <span>{t}{r.required ? <Tag color="blue" style={{ marginLeft: 6 }}>必需</Tag> : <Tag style={{ marginLeft: 6 }}>选填</Tag>}</span>
            ) },
            { title: '阶段', dataIndex: 'stage', width: 90, render: (v) => v || '-' },
            { title: '专业', dataIndex: 'specialty', width: 90, render: (v) => v || '-' },
            { title: '版本', dataIndex: 'version', width: 70, render: (v) => (v ? `v${v}` : '-') },
            { title: '截止日期', dataIndex: 'due_date', width: 120, render: (v, r) => (
              v ? <span style={{ color: r.overdue ? '#f5222d' : undefined }}>{v}{r.overdue && ' (逾期)'}</span> : '-'
            ) },
            { title: '上传人', dataIndex: ['uploader', 'name'], width: 90, render: (v) => v || '-' },
            { title: '审核人', dataIndex: ['reviewer', 'name'], width: 90, render: (v) => v || '-' },
            { title: '状态', dataIndex: 'status', width: 100, render: (s) => <Tag color={DOC_STATUS[s]?.color}>{DOC_STATUS[s]?.label || s}</Tag> },
            {
              title: '操作',
              width: 170,
              fixed: 'right',
              render: (_, r) => (
                <Space>
                  {canManage && (
                    <Upload
                      showUploadList={false}
                      action={`/api/documents/${r.id}/upload`}
                      headers={{ Authorization: `Bearer ${tokenStore.get()}` }}
                      onChange={(info) => {
                        if (info.file.status === 'done') { message.success('上传成功，待审核'); loadItems() }
                        else if (info.file.status === 'error') message.error('上传失败')
                      }}
                    >
                      <a><UploadOutlined /> 上传</a>
                    </Upload>
                  )}
                  {canReview && (
                    <a
                      onClick={() => openReview(r)}
                      style={{ color: ['pending_review', 'returned'].includes(r.status) ? undefined : '#bbb' }}
                    >
                      审核
                    </a>
                  )}
                  {!canManage && !canReview && <Tooltip title="无权限">-</Tooltip>}
                </Space>
              ),
            },
          ]}
        />
      )}

      <Modal title={`审核 - ${reviewTarget?.name || ''}`} open={!!reviewTarget} onOk={submitReview} onCancel={() => setReviewTarget(null)} destroyOnClose>
        {reviewTarget && reviewTarget.version === 0 && (
          <div style={{ color: '#fa8c16', marginBottom: 12 }}>该条目尚未上传文件，建议先上传再审核。</div>
        )}
        <Form form={reviewForm} layout="vertical">
          <Form.Item name="approved" label="审核通过" valuePropName="checked">
            <Switch checkedChildren="通过" unCheckedChildren="退回" defaultChecked />
          </Form.Item>
          <Form.Item name="review_remark" label="审核意见">
            <Input.TextArea rows={3} placeholder="退回时建议填写原因" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="新增资料条目" open={addOpen} onOk={addItem} onCancel={() => setAddOpen(false)} destroyOnClose>
        <Form form={addForm} layout="vertical" initialValues={{ required: true }}>
          <Form.Item name="name" label="资料名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Space size="large" style={{ display: 'flex' }}>
            <Form.Item name="stage" label="阶段" style={{ flex: 1 }}><Input placeholder="开工/主体/竣工" /></Form.Item>
            <Form.Item name="specialty" label="专业" style={{ flex: 1 }}><Input placeholder="土建/安装" /></Form.Item>
          </Space>
          <Form.Item name="category" label="资料类型"><Input /></Form.Item>
          <Form.Item name="required" label="是否必需" valuePropName="checked"><Switch defaultChecked /></Form.Item>
        </Form>
      </Modal>

      <Modal title="资料模板库" open={tplOpen} onOk={applyTemplate} okText="套用全部模板生成清单" onCancel={() => setTplOpen(false)} width={640}>
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={templates}
          columns={[
            { title: '模板名称', dataIndex: 'name' },
            { title: '阶段', dataIndex: 'stage', render: (v) => v || '-' },
            { title: '专业', dataIndex: 'specialty', render: (v) => v || '-' },
            { title: '必需', dataIndex: 'required', render: (v) => (v ? <Tag color="blue">必需</Tag> : <Tag>选填</Tag>) },
          ]}
        />
        <div style={{ color: '#999', fontSize: 12, marginTop: 8 }}>点击下方按钮将以上模板套用到当前项目（同名条目自动去重）。</div>
      </Modal>
    </div>
  )
}
