import { useEffect, useState } from 'react'
import {
  Tabs, Table, Tag, Space, Button, Modal, Form, Input, Select, message, Transfer,
} from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import http from '../api/client'
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

export default function SystemUsers() {
  return (
    <Tabs
      items={[
        { key: 'users', label: '用户管理', children: <Space direction="vertical" style={{ width: '100%' }}><UsersTab /></Space> },
        { key: 'roles', label: '角色权限', children: <RolesTab /> },
      ]}
    />
  )
}
