import { useMemo, useState } from 'react'
import { Layout, Menu, Avatar, Dropdown, Breadcrumb, Tooltip } from 'antd'
import {
  DashboardOutlined,
  ProjectOutlined,
  SolutionOutlined,
  SafetyCertificateOutlined,
  FileTextOutlined,
  AccountBookOutlined,
  MoneyCollectOutlined,
  FolderOpenOutlined,
  AlertOutlined,
  TeamOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  HomeOutlined,
} from '@ant-design/icons'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { brand } from '../theme'

const { Header, Sider, Content } = Layout

const MENU = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '工作台', perm: 'dashboard' },
  { key: '/projects', icon: <ProjectOutlined />, label: '项目中心', perm: 'project' },
  { key: '/tenders', icon: <SolutionOutlined />, label: '招投标', perm: 'tender' },
  { key: '/qualifications', icon: <SafetyCertificateOutlined />, label: '资质合规', perm: 'qualification' },
  { key: '/documents', icon: <FileTextOutlined />, label: '工程资料', perm: 'document' },
  { key: '/costs', icon: <AccountBookOutlined />, label: '成本管理', perm: 'cost' },
  { key: '/finance', icon: <MoneyCollectOutlined />, label: '财税账本', perm: 'finance' },
  { key: '/receivables', icon: <MoneyCollectOutlined />, label: '回款清欠', perm: 'receivable' },
  { key: '/labor', icon: <TeamOutlined />, label: '劳务法务', perm: 'labor' },
  { key: '/files', icon: <FolderOpenOutlined />, label: '文件中心', perm: 'file' },
  { key: '/alerts', icon: <AlertOutlined />, label: '预警中心', perm: 'alert' },
  { key: '/system', icon: <SettingOutlined />, label: '系统设置', perm: 'system' },
]

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, has } = useAuth()

  const items = useMemo(
    () =>
      MENU.filter((m) => has(m.perm)).map((m) => ({ key: m.key, icon: m.icon, label: m.label })),
    [user],
  )

  const current = MENU.find((m) => m.key === location.pathname)

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        trigger={null}
        width={232}
        style={{
          background: `linear-gradient(180deg, ${brand.siderTop} 0%, ${brand.siderBottom} 100%)`,
          boxShadow: '2px 0 16px rgba(11, 31, 58, 0.18)',
          position: 'sticky',
          top: 0,
          height: '100vh',
          overflow: 'hidden',
        }}
      >
        <div className="sider-brand">
          <div className="logo-mark">
            <SafetyCertificateOutlined />
          </div>
          {!collapsed && (
            <div style={{ overflow: 'hidden' }}>
              <div className="logo-text">施工运营托管</div>
              <div className="logo-sub">OPERATION PLATFORM</div>
            </div>
          )}
        </div>
        <div className="sider-menu">
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[location.pathname]}
            items={items}
            onClick={({ key }) => navigate(key)}
            style={{ background: 'transparent', borderInlineEnd: 'none' }}
          />
        </div>
      </Sider>
      <Layout>
        <Header
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 1px 8px rgba(15, 23, 42, 0.06)',
            position: 'sticky',
            top: 0,
            zIndex: 10,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Tooltip title={collapsed ? '展开菜单' : '收起菜单'}>
              <span
                onClick={() => setCollapsed((c) => !c)}
                style={{ fontSize: 18, cursor: 'pointer', color: '#475569', display: 'flex' }}
              >
                {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              </span>
            </Tooltip>
            <Breadcrumb
              items={[
                { title: <HomeOutlined /> },
                { title: current?.label || '工作台' },
              ]}
            />
          </div>
          <Dropdown
            menu={{
              items: [{ key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: logout }],
            }}
          >
            <span
              style={{
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '6px 12px',
                borderRadius: 10,
                transition: 'background .2s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = '#f1f5f9')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <Avatar size={32} style={{ background: brand.gradient }} icon={<UserOutlined />} />
              <span style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.25 }}>
                <span style={{ fontWeight: 600, fontSize: 13 }}>{user?.name}</span>
                {user?.roles?.[0] && (
                  <span style={{ fontSize: 11, color: '#94a3b8' }}>{user.roles[0].name}</span>
                )}
              </span>
            </span>
          </Dropdown>
        </Header>
        <Content style={{ margin: 20 }}>
          <div
            className="app-content-enter"
            key={location.pathname}
            style={{
              background: '#fff',
              borderRadius: 14,
              padding: 24,
              minHeight: 'calc(100vh - 64px - 40px)',
              boxShadow: '0 1px 2px rgba(15,23,42,0.04), 0 6px 20px rgba(15,23,42,0.05)',
            }}
          >
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}
