import { useEffect, useState } from 'react'
import {
  Tabs, Table, Tag, Space, Button, Modal, Form, Input, Select, message, Transfer, Card, Row, Col, Upload, Descriptions,
} from 'antd'
import { PlusOutlined, InboxOutlined } from '@ant-design/icons'
import http, { tokenStore } from '../api/client'
import type { ApiResponse, PageResult, UserRow, RoleRow } from '../api/types'

interface PermItem { code: string; name: string; type: string }

function UsersTab() {
  const [rows, setRows] = useState<UserRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [roles, setRoles] = useState<RoleRow[]>([])
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()
  const [authTarget, setAuthTarget] = useState<UserRow | null>(null)
  const [projects, setProjects] = useState<{ id: number; code: string; name: string }[]>([])
  const [authKeys, setAuthKeys] = useState<string[]>([])

  const load = () => {
    setLoading(true)
    http.get<ApiResponse<PageResult<UserRow>>>('/system/users', { params: { page, page_size: 10 } })
      .then(({ data }) => { setRows(data.data.items); setTotal(data.data.total) })
      .finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [page])
  useEffect(() => {
    http.get<ApiResponse<RoleRow[]>>('/system/roles').then(({ data }) => setRoles(data.data))
  }, [])

  const create = async () => {
    const v = await form.validateFields()
    await http.post('/system/users', v)
    message.success('已创建用户')
    setOpen(false)
    form.resetFields()
    load()
  }

  const openAuth = async (u: UserRow) => {
    setAuthTarget(u)
    const [allProj, userProj] = await Promise.all([
      http.get<ApiResponse<PageResult<{ id: number; code: string; name: string }>>>('/projects', { params: { page_size: 200 } }),
      http.get<ApiResponse<{ id: number }[]>>(`/system/users/${u.id}/projects`),
    ])
    setProjects(allProj.data.data.items)
    setAuthKeys(userProj.data.data.map((p) => String(p.id)))
  }
  const saveAuth = async () => {
    await http.put(`/system/users/${authTarget!.id}/projects`, { project_ids: authKeys.map(Number) })
    message.success('项目授权已保存')
    setAuthTarget(null)
  }

  return (
    <>
      <Button type="primary" ghost icon={<PlusOutlined />} style={{ marginBottom: 16 }} onClick={() => setOpen(true)}>
        新增用户
      </Button>
      <Table
        scroll={{ x: 'max-content' }}
        rowKey="id" loading={loading} dataSource={rows}
        pagination={{ current: page, pageSize: 10, total, onChange: setPage }}
        columns={[
          { title: '用户名', dataIndex: 'username' },
          { title: '姓名', dataIndex: 'name' },
          { title: '手机', dataIndex: 'phone', render: (v) => v || '-' },
          { title: '角色', dataIndex: 'roles', render: (rs: RoleRow[]) => rs.map((r) => <Tag key={r.id} color="blue">{r.name}</Tag>) },
          { title: '状态', dataIndex: 'status', render: (s) => <Tag color={s === 'enabled' ? 'success' : 'default'}>{s === 'enabled' ? '启用' : '停用'}</Tag> },
          { title: '最近登录', dataIndex: 'last_login_at', render: (v) => (v ? new Date(v).toLocaleString('zh-CN') : '-') },
          {
            title: '操作',
            width: 110,
            fixed: 'right',
            render: (_: unknown, r: UserRow) => (
              <a onClick={() => openAuth(r)}>项目授权</a>
            ),
          },
        ]}
      />
      <Modal title="新增用户" open={open} onOk={create} onCancel={() => setOpen(false)} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true, min: 2 }]}><Input /></Form.Item>
          <Form.Item name="password" label="初始密码" rules={[{ required: true, min: 6 }]}><Input.Password /></Form.Item>
          <Form.Item name="name" label="姓名" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="phone" label="手机"><Input /></Form.Item>
          <Form.Item name="role_ids" label="角色">
            <Select mode="multiple" options={roles.map((r) => ({ value: r.id, label: r.name }))} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal title={`项目授权 - ${authTarget?.name || ''}`} open={!!authTarget} onOk={saveAuth} onCancel={() => setAuthTarget(null)} width={680} destroyOnClose>
        <div style={{ color: '#999', fontSize: 12, marginBottom: 12 }}>
          数据范围为「按项目授权」的用户（如项目负责人）仅能查看/操作被授权的项目及其成本、财税、回款、资料等数据；超管与全局角色不受限。
        </div>
        <Transfer
          dataSource={projects.map((p) => ({ key: String(p.id), title: `${p.code} ${p.name}` }))}
          targetKeys={authKeys}
          onChange={(keys) => setAuthKeys(keys as string[])}
          render={(item) => item.title}
          titles={['全部项目', '已授权']}
          listStyle={{ width: 300, height: 360 }}
        />
      </Modal>
    </>
  )
}

function RolesTab() {
  const [roles, setRoles] = useState<RoleRow[]>([])
  const [perms, setPerms] = useState<PermItem[]>([])
  const [editing, setEditing] = useState<RoleRow | null>(null)
  const [targetKeys, setTargetKeys] = useState<string[]>([])

  const load = () => http.get<ApiResponse<RoleRow[]>>('/system/roles').then(({ data }) => setRoles(data.data))
  useEffect(() => { load() }, [])
  useEffect(() => {
    http.get<ApiResponse<PermItem[]>>('/system/permissions').then(({ data }) => setPerms(data.data))
  }, [])

  const openEdit = (r: RoleRow) => {
    setEditing(r)
    setTargetKeys(r.permissions.map((p) => p.code))
  }

  const save = async () => {
    await http.put(`/system/roles/${editing!.id}`, { permission_codes: targetKeys })
    message.success('权限已保存')
    setEditing(null)
    load()
  }

  return (
    <>
      <Table
        scroll={{ x: 'max-content' }}
        rowKey="id" dataSource={roles} pagination={false}
        columns={[
          { title: '编码', dataIndex: 'code' },
          { title: '角色名称', dataIndex: 'name' },
          { title: '数据范围', dataIndex: 'data_scope' },
          { title: '权限数', dataIndex: 'permissions', render: (p: PermItem[]) => p.length },
          { title: '操作', width: 110, fixed: 'right', render: (_, r) => <a onClick={() => openEdit(r)}>配置权限</a> },
        ]}
      />
      <Modal title={`配置权限 - ${editing?.name}`} open={!!editing} onOk={save} onCancel={() => setEditing(null)} width={680} destroyOnClose>
        <Transfer
          dataSource={perms.map((p) => ({ key: p.code, title: `${p.name}（${p.code}）` }))}
          targetKeys={targetKeys}
          onChange={(keys) => setTargetKeys(keys as string[])}
          render={(item) => item.title}
          titles={['可选权限', '已授权']}
          listStyle={{ width: 280, height: 360 }}
        />
      </Modal>
    </>
  )
}

interface AuditRow {
  id: number; username?: string; action: string; target_type?: string; target_id?: string; ip?: string; created_at?: string
}

function AuditTab() {
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

interface IntegrationLogRow {
  id: number; channel: string; provider: string; action: string; target?: string
  status: string; response_summary?: string; operator_name?: string; created_at: string
}

const CHANNEL_LABEL: Record<string, string> = { sms: '短信', esign: '电子签', ocr: 'OCR' }

function IntegrationsTab() {
  const [providers, setProviders] = useState<{ sms: string; esign: string; ocr: string } | null>(null)
  const [logs, setLogs] = useState<IntegrationLogRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [smsOpen, setSmsOpen] = useState(false)
  const [esignOpen, setEsignOpen] = useState(false)
  const [ocrOpen, setOcrOpen] = useState(false)
  const [ocrResult, setOcrResult] = useState<Record<string, string> | null>(null)
  const [smsForm] = Form.useForm()
  const [esignForm] = Form.useForm()

  const load = () => {
    http.get<ApiResponse<PageResult<IntegrationLogRow>>>('/integrations/logs', { params: { page, page_size: 10 } })
      .then(({ data }) => { setLogs(data.data.items); setTotal(data.data.total) })
  }
  useEffect(() => { load() }, [page])
  useEffect(() => {
    http.get<ApiResponse<{ sms: string; esign: string; ocr: string }>>('/integrations/providers').then(({ data }) => setProviders(data.data))
  }, [])

  const sendSms = async () => {
    const v = await smsForm.validateFields()
    const { data } = await http.post<ApiResponse<{ message_id: string }>>('/integrations/sms', v)
    message.success(`短信已发送（${data.data.message_id}）`)
    setSmsOpen(false); smsForm.resetFields(); load()
  }
  const initEsign = async () => {
    const v = await esignForm.validateFields()
    const { data } = await http.post<ApiResponse<{ sign_url: string }>>('/integrations/esign', {
      doc_name: v.doc_name, signers: (v.signers || '').split(/[,，\s]+/).filter(Boolean),
    })
    Modal.success({ title: '电子签发起成功', content: `签署链接：${data.data.sign_url}` })
    setEsignOpen(false); esignForm.resetFields(); load()
  }

  const ocrProps = {
    name: 'file',
    action: '/api/integrations/ocr',
    data: { doc_type: 'invoice' },
    headers: { Authorization: `Bearer ${tokenStore.get()}` },
    showUploadList: false,
    onChange(info: { file: { status?: string; response?: ApiResponse<{ fields: Record<string, string> }> } }) {
      if (info.file.status === 'done') {
        setOcrResult(info.file.response?.data.fields || {})
        message.success('OCR 识别完成')
        load()
      } else if (info.file.status === 'error') {
        message.error('OCR 识别失败')
      }
    },
  }

  return (
    <>
      {providers && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Space size="large">
            <span>当前 Provider：</span>
            <span>短信 <Tag color={providers.sms === 'mock' ? 'default' : 'green'}>{providers.sms}</Tag></span>
            <span>电子签 <Tag color={providers.esign === 'mock' ? 'default' : 'green'}>{providers.esign}</Tag></span>
            <span>OCR <Tag color={providers.ocr === 'mock' ? 'default' : 'green'}>{providers.ocr}</Tag></span>
            <span style={{ color: '#999', fontSize: 12 }}>（mock 为内置模拟，不外发数据；配置 APP_SMS_PROVIDER 等可切换真实厂商）</span>
          </Space>
        </Card>
      )}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col><Button type="primary" ghost onClick={() => setSmsOpen(true)}>发送短信测试</Button></Col>
        <Col><Button type="primary" ghost onClick={() => setEsignOpen(true)}>发起电子签章</Button></Col>
        <Col><Button type="primary" ghost onClick={() => { setOcrResult(null); setOcrOpen(true) }}>OCR 识别测试</Button></Col>
      </Row>

      <Table
        rowKey="id" dataSource={logs} pagination={{ current: page, pageSize: 10, total, onChange: setPage }}
        columns={[
          { title: '时间', dataIndex: 'created_at', render: (v) => new Date(v).toLocaleString('zh-CN') },
          { title: '渠道', dataIndex: 'channel', render: (c) => <Tag>{CHANNEL_LABEL[c] || c}</Tag> },
          { title: 'Provider', dataIndex: 'provider' },
          { title: '动作', dataIndex: 'action' },
          { title: '目标', dataIndex: 'target', ellipsis: true, render: (v) => v || '-' },
          { title: '状态', dataIndex: 'status', render: (s) => <Tag color={s === 'success' ? 'success' : 'error'}>{s === 'success' ? '成功' : '失败'}</Tag> },
          { title: '操作人', dataIndex: 'operator_name', render: (v) => v || '-' },
        ]}
      />

      <Modal title="发送短信测试" open={smsOpen} onOk={sendSms} onCancel={() => setSmsOpen(false)} destroyOnClose>
        <Form form={smsForm} layout="vertical" initialValues={{ content: '【示范建工】您的债权已逾期，请及时安排回款。' }}>
          <Form.Item name="to" label="手机号" rules={[{ required: true }]}><Input placeholder="13800000000" /></Form.Item>
          <Form.Item name="content" label="短信内容" rules={[{ required: true }]}><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
      <Modal title="发起电子签章" open={esignOpen} onOk={initEsign} onCancel={() => setEsignOpen(false)} destroyOnClose>
        <Form form={esignForm} layout="vertical">
          <Form.Item name="doc_name" label="文件名称" rules={[{ required: true }]}><Input placeholder="施工承包合同" /></Form.Item>
          <Form.Item name="signers" label="签署方（逗号分隔）"><Input placeholder="甲方,乙方" /></Form.Item>
        </Form>
      </Modal>
      <Modal title="OCR 识别测试（发票）" open={ocrOpen} onCancel={() => setOcrOpen(false)} footer={<Button onClick={() => setOcrOpen(false)}>关闭</Button>}>
        <Upload.Dragger {...ocrProps}>
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p>点击或拖拽发票图片到此处识别（mock 返回模拟字段）</p>
        </Upload.Dragger>
        {ocrResult && (
          <Descriptions bordered size="small" column={1} style={{ marginTop: 16 }}>
            {Object.entries(ocrResult).map(([k, v]) => <Descriptions.Item key={k} label={k}>{v}</Descriptions.Item>)}
          </Descriptions>
        )}
      </Modal>
    </>
  )
}

export default function System() {
  return (
    <Tabs
      items={[
        { key: 'users', label: '用户管理', children: <Space direction="vertical" style={{ width: '100%' }}><UsersTab /></Space> },
        { key: 'roles', label: '角色权限', children: <RolesTab /> },
        { key: 'integration', label: '第三方集成', children: <IntegrationsTab /> },
        { key: 'audit', label: '操作日志', children: <AuditTab /> },
      ]}
    />
  )
}
