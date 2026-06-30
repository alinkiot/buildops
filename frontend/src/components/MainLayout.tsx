import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Layout, Menu, Avatar, Dropdown, Breadcrumb, Tooltip, Tabs } from 'antd'
import type { MenuProps } from 'antd'
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
  ReloadOutlined,
  CloseOutlined,
  VerticalLeftOutlined,
  VerticalRightOutlined,
  ApiOutlined,
  AuditOutlined,
} from '@ant-design/icons'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { brand } from '../theme'

const { Header, Sider, Content } = Layout

interface MenuItem {
  key: string
  icon: React.ReactNode
  label: string
  perm: string
  children?: { key: string; icon: React.ReactNode; label: string }[]
}

const MENU: MenuItem[] = [
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
  {
    key: '/system', icon: <SettingOutlined />, label: '系统设置', perm: 'system',
    children: [
      { key: '/system/users', icon: <UserOutlined />, label: '用户中心' },
      { key: '/system/integrations', icon: <ApiOutlined />, label: '第三方集成' },
      { key: '/system/audit', icon: <AuditOutlined />, label: '操作日志' },
    ],
  },
]

interface TabItem {
  key: string
  label: string
  closable: boolean
}

// 默认首页标签不可关闭
const HOME_TAB: TabItem = { key: '/dashboard', label: '工作台', closable: false }

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [tabs, setTabs] = useState<TabItem[]>([HOME_TAB])
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, has } = useAuth()

  const items = useMemo(
    () =>
      MENU.filter((m) => has(m.perm)).map((m) => ({
        key: m.key,
        icon: m.icon,
        label: m.label,
        children: m.children?.map((c) => ({ key: c.key, icon: c.icon, label: c.label })),
      })),
    [user],
  )

  // 扁平化菜单用于查找当前路由对应的菜单项
  const flatMenu = useMemo(() => {
    const list: { key: string; label: string }[] = []
    MENU.forEach((m) => {
      if (m.children) {
        m.children.forEach((c) => list.push({ key: c.key, label: c.label }))
      } else {
        list.push({ key: m.key, label: m.label })
      }
    })
    return list
  }, [])

  const current = flatMenu.find((m) => m.key === location.pathname)

  // 路由变化时自动添加标签
  useEffect(() => {
    const path = location.pathname
    const menu = flatMenu.find((m) => m.key === path)
    if (!menu) return
    setTabs((prev) => {
      if (prev.some((t) => t.key === path)) return prev
      return [...prev, { key: path, label: menu.label, closable: path !== '/dashboard' }]
    })
  }, [location.pathname, flatMenu])

  // 切换标签
  const onTabChange = useCallback(
    (key: string) => {
      navigate(key)
    },
    [navigate],
  )

  // 关闭标签
  const onTabEdit = useCallback(
    (targetKey: unknown, action: 'add' | 'remove') => {
      if (action !== 'remove' || typeof targetKey !== 'string') return
      setTabs((prev) => {
        const idx = prev.findIndex((t) => t.key === targetKey)
        const newTabs = prev.filter((t) => t.key !== targetKey)
        // 如果关闭的是当前激活标签，跳到相邻标签
        if (targetKey === location.pathname) {
          const next = newTabs[Math.min(idx, newTabs.length - 1)]
          if (next) navigate(next.key)
        }
        return newTabs
      })
    },
    [location.pathname, navigate],
  )

  // ===== 右键菜单 =====
  const [contextMenu, setContextMenu] = useState<{ tabKey: string; x: number; y: number } | null>(null)

  // 点击任意位置关闭菜单
  useEffect(() => {
    if (!contextMenu) return
    const hide = (e: MouseEvent) => {
      // 如果点击在右键菜单内部则不关闭（由菜单 onClick 自行关闭）
      const target = e.target as HTMLElement
      if (target.closest('.tab-context-menu')) return
      setContextMenu(null)
    }
    // 延迟绑定，避免当前这次右键事件冒泡立即触发关闭
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', hide)
      document.addEventListener('contextmenu', hide)
    }, 0)
    return () => {
      clearTimeout(timer)
      document.removeEventListener('mousedown', hide)
      document.removeEventListener('contextmenu', hide)
    }
  }, [contextMenu])

  const contextMenuItems: MenuProps['items'] = useMemo(() => {
    if (!contextMenu) return []
    const idx = tabs.findIndex((t) => t.key === contextMenu.tabKey)
    return [
      { key: 'refresh', icon: <ReloadOutlined />, label: '刷新页面' },
      { type: 'divider' as const },
      {
        key: 'closeOthers',
        icon: <CloseOutlined />,
        label: '关闭其它',
        disabled: tabs.filter((t) => t.closable && t.key !== contextMenu.tabKey).length === 0,
      },
      {
        key: 'closeLeft',
        icon: <VerticalRightOutlined />,
        label: '关闭左侧',
        disabled: tabs.slice(0, idx).filter((t) => t.closable).length === 0,
      },
      {
        key: 'closeRight',
        icon: <VerticalLeftOutlined />,
        label: '关闭右侧',
        disabled: tabs.slice(idx + 1).filter((t) => t.closable).length === 0,
      },
    ]
  }, [contextMenu, tabs])

  const onContextMenuAction = useCallback(
    ({ key }: { key: string }) => {
      if (!contextMenu) return
      const targetKey = contextMenu.tabKey
      const idx = tabs.findIndex((t) => t.key === targetKey)

      if (key === 'refresh') {
        // 通过先导航到一个空路径再回来实现刷新
        navigate(targetKey, { replace: true })
        // 使用 key 机制强制 remount
        window.location.reload()
      } else if (key === 'closeOthers') {
        const kept = tabs.filter((t) => !t.closable || t.key === targetKey)
        setTabs(kept)
        if (!kept.some((t) => t.key === location.pathname)) {
          navigate(targetKey)
        }
      } else if (key === 'closeLeft') {
        const leftKeys = tabs.slice(0, idx).filter((t) => t.closable).map((t) => t.key)
        const kept = tabs.filter((t) => !leftKeys.includes(t.key))
        setTabs(kept)
        if (leftKeys.includes(location.pathname)) {
          navigate(targetKey)
        }
      } else if (key === 'closeRight') {
        const rightKeys = tabs.slice(idx + 1).filter((t) => t.closable).map((t) => t.key)
        const kept = tabs.filter((t) => !rightKeys.includes(t.key))
        setTabs(kept)
        if (rightKeys.includes(location.pathname)) {
          navigate(targetKey)
        }
      }
      setContextMenu(null)
    },
    [contextMenu, tabs, location.pathname, navigate],
  )

  // 为 tab 渲染带右键事件的 label — 使用事件委托，绑定在整个 tabs 容器上
  const tabsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = tabsRef.current
    if (!container) return
    const handler = (e: MouseEvent) => {
      let el = e.target as HTMLElement | null
      let tabKey: string | null = null
      while (el && el !== container) {
        tabKey = el.getAttribute('data-node-key')
        if (tabKey) break
        el = el.parentElement
      }
      if (!tabKey) return
      e.preventDefault()
      e.stopPropagation()
      setContextMenu({ tabKey, x: e.clientX, y: e.clientY })
    }
    container.addEventListener('contextmenu', handler)
    return () => container.removeEventListener('contextmenu', handler)
  }, [])

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
            defaultOpenKeys={['/system']}
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
              items: [
                { key: 'role', label: <span style={{ fontWeight: 600, color: '#334155', display: 'block', textAlign: 'center' }}>超级管理员</span>, disabled: true },
                { type: 'divider' },
                { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: logout },
              ],
            }}
          >
            <span
              style={{
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: '6px 12px',
                borderRadius: 10,
                transition: 'background .2s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = '#f1f5f9')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <Avatar size={32} style={{ background: brand.gradient }} icon={<UserOutlined />} />
            </span>
          </Dropdown>
        </Header>
        {/* 多页签标签栏 */}
        <div className="layout-tabs" ref={tabsRef}>
          <Tabs
            type="editable-card"
            hideAdd
            activeKey={location.pathname}
            onChange={onTabChange}
            onEdit={onTabEdit}
            size="small"
            items={tabs.map((t) => ({ key: t.key, label: t.label, closable: t.closable }))}
          />
        </div>
        {/* 右键菜单 */}
        {contextMenu && (
          <div
            className="tab-context-menu"
            style={{
              position: 'fixed',
              left: contextMenu.x,
              top: contextMenu.y,
              zIndex: 1050,
              boxShadow: '0 6px 16px 0 rgba(0,0,0,0.08), 0 3px 6px -4px rgba(0,0,0,0.12), 0 9px 28px 8px rgba(0,0,0,0.05)',
              borderRadius: 8,
              background: '#fff',
              padding: '4px 0',
            }}
          >
            <Menu
              items={contextMenuItems}
              onClick={onContextMenuAction}
              style={{ border: 'none', boxShadow: 'none', borderRadius: 8, minWidth: 120 }}
              className="tab-context-menu-list"
            />
          </div>
        )}
        <Content style={{ margin: 20 }}>
          <div
            className="app-content-enter"
            key={location.pathname}
            style={{
              background: '#fff',
              borderRadius: 14,
              padding: 24,
              minHeight: 'calc(100vh - 64px - 48px - 40px)',
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
