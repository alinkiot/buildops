/**
 * 经营驾驶舱 —— 全屏数据可视化大屏
 * 深色科技风格，适配 16:9 / 21:9 大屏幕，支持全屏模式
 */
import { useEffect, useState, useCallback, useRef } from 'react'
import { Spin } from 'antd'
import {
  FullscreenOutlined,
  FullscreenExitOutlined,
  CloseOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import http from '../api/client'
import type { ApiResponse, DashboardData } from '../api/types'
import './DashboardScreen.css'

/** 格式化金额（万元） */
const fmt = (v: string | number) => {
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (isNaN(n)) return '0'
  return (n / 10000).toLocaleString('zh-CN', { maximumFractionDigits: 1 })
}

/** KPI 数字卡片 */
function KpiCard({ title, value, suffix, icon, color, delay }: {
  title: string; value: string | number; suffix?: string; icon: string; color: string; delay: number
}) {
  return (
    <div className="screen-kpi" style={{ '--accent': color, animationDelay: `${delay}ms` } as React.CSSProperties}>
      <div className="screen-kpi__icon">{icon}</div>
      <div className="screen-kpi__body">
        <div className="screen-kpi__label">{title}</div>
        <div className="screen-kpi__value">
          {value}
          {suffix && <span className="screen-kpi__suffix">{suffix}</span>}
        </div>
      </div>
      <div className="screen-kpi__glow" />
    </div>
  )
}

/** 水平条形图 */
function BarChart({ data, maxValue }: { data: { label: string; value: number; color?: string }[]; maxValue: number }) {
  return (
    <div className="screen-bar-chart">
      {data.map((d, i) => (
        <div className="screen-bar-row" key={d.label} style={{ animationDelay: `${600 + i * 80}ms` }}>
          <span className="screen-bar-label">{d.label}</span>
          <div className="screen-bar-track">
            <div
              className="screen-bar-fill"
              style={{
                width: `${Math.max((Math.abs(d.value) / maxValue) * 100, 2)}%`,
                background: d.color || (d.value >= 0 ? 'linear-gradient(90deg, #22d3ee, #0ea5e9)' : 'linear-gradient(90deg, #f87171, #ef4444)'),
                animationDelay: `${800 + i * 80}ms`,
              }}
            />
          </div>
          <span className={`screen-bar-val ${d.value < 0 ? 'negative' : ''}`}>
            {fmt(d.value)} 万
          </span>
        </div>
      ))}
    </div>
  )
}

/** 环形进度 */
function RingProgress({ percent, size = 80, strokeWidth = 8, color = '#22d3ee', label }: {
  percent: number; size?: number; strokeWidth?: number; color?: string; label?: string
}) {
  const r = (size - strokeWidth) / 2
  const c = 2 * Math.PI * r
  const offset = c * (1 - percent / 100)
  return (
    <div className="screen-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={strokeWidth} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke={color} strokeWidth={strokeWidth}
          strokeDasharray={c} strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1.5s cubic-bezier(0.22,1,0.36,1)', transform: 'rotate(-90deg)', transformOrigin: 'center' }}
        />
      </svg>
      <div className="screen-ring__text">
        <span className="screen-ring__num">{percent}</span>
        <span className="screen-ring__unit">%</span>
      </div>
      {label && <div className="screen-ring__label">{label}</div>}
    </div>
  )
}

/** 预警分布条 */
function AlertDistribution({ data, total }: { data: { name: string; value: number }[]; total: number }) {
  const colors = ['#ef4444', '#f97316', '#3b82f6', '#64748b']
  return (
    <div className="screen-alert-dist">
      <div className="screen-alert-bar">
        {data.map((d, i) => (
          <div
            key={d.name}
            className="screen-alert-seg"
            style={{
              width: `${(d.value / total) * 100}%`,
              background: colors[i % colors.length],
              animationDelay: `${800 + i * 100}ms`,
            }}
          />
        ))}
      </div>
      <div className="screen-alert-legend">
        {data.map((d, i) => (
          <div className="screen-alert-item" key={d.name}>
            <span className="screen-alert-dot" style={{ background: colors[i % colors.length] }} />
            <span className="screen-alert-name">{d.name}</span>
            <span className="screen-alert-count">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/** 项目状态饼图 */
function StatusPie({ data }: { data: { name: string; value: number }[] }) {
  const colors = ['#3b82f6', '#22c55e', '#f59e0b', '#8b5cf6', '#06b6d4', '#f43f5e', '#64748b']
  const total = data.reduce((s, d) => s + d.value, 0)
  let cumPercent = 0

  return (
    <div className="screen-pie-container">
      <div className="screen-pie-ring">
        <svg viewBox="0 0 100 100">
          {data.map((d, i) => {
            const percent = (d.value / total) * 100
            const dashArray = `${percent} ${100 - percent}`
            const dashOffset = -cumPercent
            cumPercent += percent
            return (
              <circle
                key={d.name}
                cx="50" cy="50" r="38" fill="none"
                stroke={colors[i % colors.length]}
                strokeWidth="10"
                strokeDasharray={dashArray}
                strokeDashoffset={dashOffset}
                style={{ transition: 'all 1.2s ease' }}
                pathLength="100"
              />
            )
          })}
        </svg>
        <div className="screen-pie-center">
          <span className="screen-pie-total">{total}</span>
          <span className="screen-pie-unit">个项目</span>
        </div>
      </div>
      <div className="screen-pie-legend">
        {data.map((d, i) => (
          <div className="screen-pie-legend-item" key={d.name}>
            <span className="screen-pie-dot" style={{ background: colors[i % colors.length] }} />
            <span className="screen-pie-name">{d.name}</span>
            <span className="screen-pie-val">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function DashboardScreen() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [currentTime, setCurrentTime] = useState(new Date())
  const containerRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  // 获取数据
  useEffect(() => {
    http.get<ApiResponse<DashboardData>>('/dashboard')
      .then(({ data }) => setData(data.data))
      .finally(() => setLoading(false))
  }, [])

  // 实时时钟
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  // 全屏切换
  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen()
    } else {
      document.exitFullscreen()
    }
  }, [])

  useEffect(() => {
    const onChange = () => setIsFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', onChange)
    return () => document.removeEventListener('fullscreenchange', onChange)
  }, [])

  // ESC 退出自动进入全屏状态时回到 dashboard
  const handleClose = useCallback(() => {
    if (document.fullscreenElement) {
      document.exitFullscreen()
    }
    navigate('/dashboard')
  }, [navigate])

  if (loading) {
    return (
      <div className="screen-loading">
        <Spin size="large" />
        <p>数据加载中…</p>
      </div>
    )
  }

  if (!data) return null

  const ov = data.overview
  const maxProfit = Math.max(...data.project_profit_rank.map((p) => Math.abs(p.profit)), 1)

  return (
    <div className="dashboard-screen" ref={containerRef}>
      {/* 背景装饰 */}
      <div className="screen-bg-grid" />
      <div className="screen-bg-glow screen-bg-glow--1" />
      <div className="screen-bg-glow screen-bg-glow--2" />

      {/* 顶部标题栏 */}
      <header className="screen-header">
        <div className="screen-header__left">
          <div className="screen-header__logo">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <rect width="28" height="28" rx="6" fill="url(#logo-grad)" />
              <path d="M7 20V10l7-4 7 4v10l-7 4-7-4z" stroke="#fff" strokeWidth="1.5" fill="none" />
              <path d="M14 6v18M7 10l7 4 7-4" stroke="#fff" strokeWidth="1.2" opacity="0.6" />
              <defs><linearGradient id="logo-grad" x1="0" y1="0" x2="28" y2="28"><stop stopColor="#1668dc"/><stop offset="1" stopColor="#0ea5e9"/></linearGradient></defs>
            </svg>
          </div>
          <div>
            <h1 className="screen-header__title">施工运营经营驾驶舱</h1>
            <p className="screen-header__sub">CONSTRUCTION OPERATIONS DASHBOARD</p>
          </div>
        </div>
        <div className="screen-header__right">
          <div className="screen-header__time">
            <span className="screen-header__date">
              {currentTime.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'short' })}
            </span>
            <span className="screen-header__clock">
              {currentTime.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          </div>
          <button className="screen-ctrl-btn" onClick={toggleFullscreen} title={isFullscreen ? '退出全屏' : '全屏显示'}>
            {isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
          </button>
          <button className="screen-ctrl-btn screen-ctrl-btn--close" onClick={handleClose} title="退出大屏">
            <CloseOutlined />
          </button>
        </div>
      </header>

      {/* KPI 概览条 */}
      <section className="screen-kpi-bar">
        <KpiCard title="在建项目" value={ov.ongoing_count} suffix={`/ ${ov.project_count}`} icon="📐" color="#3b82f6" delay={0} />
        <KpiCard title="合同总额" value={fmt(ov.contract_amount)} suffix="万" icon="📄" color="#06b6d4" delay={80} />
        <KpiCard title="累计回款" value={fmt(ov.received_amount)} suffix="万" icon="💰" color="#22c55e" delay={160} />
        <KpiCard title="毛利" value={fmt(ov.profit_amount)} suffix="万" icon="📈" color="#8b5cf6" delay={240} />
        <KpiCard title="待回款" value={fmt(ov.receivable_amount)} suffix="万" icon="⏳" color="#f59e0b" delay={320} />
        <KpiCard title="待处理预警" value={ov.pending_alert_count} suffix={`/ ${ov.alert_count}`} icon="🚨" color="#ef4444" delay={400} />
      </section>

      {/* 主内容三栏 */}
      <main className="screen-main">
        {/* 左列 */}
        <section className="screen-panel screen-panel--left">
          <div className="screen-card">
            <div className="screen-card__header">
              <span className="screen-card__title">项目状态分布</span>
            </div>
            <div className="screen-card__body">
              <StatusPie data={data.project_by_status} />
            </div>
          </div>

          {data.modules && (
            <div className="screen-card">
              <div className="screen-card__header">
                <span className="screen-card__title">核心健康度</span>
              </div>
              <div className="screen-card__body">
                <div className="screen-health-grid">
                  <RingProgress
                    percent={data.modules.qualification.health_score}
                    color={data.modules.qualification.expired > 0 ? '#ef4444' : '#22d3ee'}
                    label="资质"
                  />
                  <RingProgress
                    percent={data.modules.document.completeness}
                    color={data.modules.document.missing > 0 ? '#f97316' : '#22c55e'}
                    label="资料"
                  />
                  <RingProgress
                    percent={Math.max(0, 100 - Math.abs(data.modules.cost.deviation_rate))}
                    color={data.modules.cost.deviation_rate > 10 ? '#ef4444' : '#3b82f6'}
                    label="成本"
                  />
                  <RingProgress
                    percent={data.modules.bid.win_rate}
                    color="#8b5cf6"
                    label="中标率"
                  />
                </div>
              </div>
            </div>
          )}
        </section>

        {/* 中列 */}
        <section className="screen-panel screen-panel--center">
          <div className="screen-card screen-card--full">
            <div className="screen-card__header">
              <span className="screen-card__title">项目利润排行</span>
              <span className="screen-card__badge">回款 - 成本 · TOP {data.project_profit_rank.length}</span>
            </div>
            <div className="screen-card__body">
              <BarChart
                data={data.project_profit_rank.map((p) => ({
                  label: p.name.length > 10 ? p.name.slice(0, 10) + '…' : p.name,
                  value: p.profit,
                }))}
                maxValue={maxProfit}
              />
            </div>
          </div>
        </section>

        {/* 右列 */}
        <section className="screen-panel screen-panel--right">
          <div className="screen-card">
            <div className="screen-card__header">
              <span className="screen-card__title">预警等级分布</span>
              <span className="screen-card__badge">共 {ov.alert_count} 条</span>
            </div>
            <div className="screen-card__body">
              <AlertDistribution data={data.alert_by_level} total={Math.max(ov.alert_count, 1)} />
            </div>
          </div>

          <div className="screen-card">
            <div className="screen-card__header">
              <span className="screen-card__title">预警来源</span>
            </div>
            <div className="screen-card__body">
              <div className="screen-source-list">
                {data.alert_by_source.map((s, i) => (
                  <div className="screen-source-row" key={s.name} style={{ animationDelay: `${900 + i * 60}ms` }}>
                    <span className="screen-source-rank">#{i + 1}</span>
                    <span className="screen-source-name">{s.name}</span>
                    <div className="screen-source-bar">
                      <div
                        className="screen-source-fill"
                        style={{ width: `${(s.value / Math.max(ov.alert_count, 1)) * 100}%` }}
                      />
                    </div>
                    <span className="screen-source-val">{s.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {data.modules && (
            <div className="screen-card">
              <div className="screen-card__header">
                <span className="screen-card__title">经营快报</span>
              </div>
              <div className="screen-card__body">
                <div className="screen-quick-stats">
                  <div className="screen-stat-item">
                    <span className="screen-stat-label">财税净利润</span>
                    <span className="screen-stat-value" style={{ color: '#a78bfa' }}>{fmt(data.modules.finance.net_profit)} 万</span>
                  </div>
                  <div className="screen-stat-item">
                    <span className="screen-stat-label">待回总额</span>
                    <span className="screen-stat-value" style={{ color: '#fbbf24' }}>{fmt(data.modules.receivable.total_outstanding)} 万</span>
                  </div>
                  <div className="screen-stat-item">
                    <span className="screen-stat-label">超预算项目</span>
                    <span className="screen-stat-value" style={{ color: '#f87171' }}>{data.modules.cost.over_budget_projects} 个</span>
                  </div>
                  <div className="screen-stat-item">
                    <span className="screen-stat-label">在场工人</span>
                    <span className="screen-stat-value" style={{ color: '#34d399' }}>{data.modules.labor.onsite} 人</span>
                  </div>
                  <div className="screen-stat-item">
                    <span className="screen-stat-label">保证金未退</span>
                    <span className="screen-stat-value" style={{ color: '#fb923c' }}>{fmt(data.modules.bid.deposit_outstanding)} 万</span>
                  </div>
                  <div className="screen-stat-item">
                    <span className="screen-stat-label">无票占比</span>
                    <span className="screen-stat-value" style={{ color: data.modules.finance.no_invoice_ratio > 10 ? '#f87171' : '#94a3b8' }}>
                      {data.modules.finance.no_invoice_ratio}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>
      </main>

      {/* 底部装饰线 */}
      <div className="screen-footer-line" />
    </div>
  )
}
