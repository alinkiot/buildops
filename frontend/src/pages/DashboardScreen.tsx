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

/** 回款趋势 SVG 折线/柱状图 */
function TrendChart({ data }: { data: Array<{ month: string; planned: number; actual: number }> }) {
  if (!data.length) return <div style={{ color: '#64748b', fontSize: 12 }}>暂无数据</div>
  const maxVal = Math.max(...data.flatMap((d) => [d.planned, d.actual]), 1)
  const w = 400, h = 140, px = 40, py = 16
  const chartW = w - px * 2, chartH = h - py * 2
  const stepX = chartW / Math.max(data.length - 1, 1)

  const plannedPoints = data.map((d, i) => `${px + i * stepX},${py + chartH - (d.planned / maxVal) * chartH}`)
  const actualPoints = data.map((d, i) => `${px + i * stepX},${py + chartH - (d.actual / maxVal) * chartH}`)

  return (
    <div className="screen-trend-chart">
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
        {/* grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((r) => (
          <line key={r} x1={px} x2={w - px} y1={py + chartH * (1 - r)} y2={py + chartH * (1 - r)}
            stroke="rgba(148,163,184,0.1)" strokeDasharray="3,3" />
        ))}
        {/* planned line */}
        <polyline points={plannedPoints.join(' ')} fill="none" stroke="#64748b" strokeWidth="1.5" strokeDasharray="4,3" />
        {/* actual line */}
        <polyline points={actualPoints.join(' ')} fill="none" stroke="#22d3ee" strokeWidth="2" />
        {/* actual dots */}
        {data.map((d, i) => (
          <circle key={i} cx={px + i * stepX} cy={py + chartH - (d.actual / maxVal) * chartH}
            r="3" fill="#22d3ee" stroke="#070c1a" strokeWidth="1.5" />
        ))}
        {/* x labels */}
        {data.map((d, i) => (
          <text key={i} x={px + i * stepX} y={h - 2} textAnchor="middle" fontSize="9" fill="#64748b">{d.month}</text>
        ))}
        {/* y labels */}
        {[0, 0.5, 1].map((r) => (
          <text key={r} x={px - 6} y={py + chartH * (1 - r) + 3} textAnchor="end" fontSize="8" fill="#64748b">
            {((maxVal * r) / 10000).toFixed(0)}万
          </text>
        ))}
      </svg>
      <div className="screen-trend-legend">
        <span><i style={{ background: '#22d3ee' }} />实际回款</span>
        <span><i style={{ background: '#64748b' }} />计划回款</span>
      </div>
    </div>
  )
}

/** 合同额 Top5 水平条形图 */
function ContractTop5Chart({ data }: { data: Array<{ name: string; contract_amount: number; received_amount: number }> }) {
  if (!data.length) return <div style={{ color: '#64748b', fontSize: 12 }}>暂无数据</div>
  const maxVal = Math.max(...data.map((d) => d.contract_amount), 1)
  return (
    <div className="screen-bar-chart">
      {data.map((d, i) => (
        <div className="screen-bar-row" key={d.name} style={{ animationDelay: `${600 + i * 80}ms` }}>
          <span className="screen-bar-label">{d.name.length > 8 ? d.name.slice(0, 8) + '…' : d.name}</span>
          <div className="screen-bar-track" style={{ position: 'relative' }}>
            <div className="screen-bar-fill" style={{
              width: `${(d.contract_amount / maxVal) * 100}%`,
              background: 'linear-gradient(90deg, rgba(59,130,246,0.4), rgba(59,130,246,0.7))',
              animationDelay: `${800 + i * 80}ms`,
            }} />
            <div className="screen-bar-fill" style={{
              width: `${(d.received_amount / maxVal) * 100}%`,
              background: 'linear-gradient(90deg, #22d3ee, #06b6d4)',
              position: 'absolute', top: 0, left: 0, height: '100%',
              animationDelay: `${900 + i * 80}ms`,
            }} />
          </div>
          <span className="screen-bar-val">{(d.contract_amount / 10000).toFixed(0)}万</span>
        </div>
      ))}
    </div>
  )
}

/** 成本结构分布饼图 */
function CostPie({ data }: { data: { name: string; value: number }[] }) {
  const colors = ['#3b82f6', '#22d3ee', '#8b5cf6', '#f59e0b', '#22c55e', '#f43f5e', '#64748b']
  const total = data.reduce((s, d) => s + d.value, 0)
  if (!total) return <div style={{ color: '#64748b', fontSize: 12 }}>暂无数据</div>
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
              <circle key={d.name} cx="50" cy="50" r="38" fill="none"
                stroke={colors[i % colors.length]} strokeWidth="10"
                strokeDasharray={dashArray} strokeDashoffset={dashOffset}
                style={{ transition: 'all 1.2s ease' }} pathLength="100" />
            )
          })}
        </svg>
        <div className="screen-pie-center">
          <span className="screen-pie-total">{(total / 10000).toFixed(0)}</span>
          <span className="screen-pie-unit">万元</span>
        </div>
      </div>
      <div className="screen-pie-legend">
        {data.map((d, i) => (
          <div className="screen-pie-legend-item" key={d.name}>
            <span className="screen-pie-dot" style={{ background: colors[i % colors.length] }} />
            <span className="screen-pie-name">{d.name}</span>
            <span className="screen-pie-val">{(d.value / 10000).toFixed(0)}万</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/** 待办预警滚动列表 */
function AlertScroll({ alerts }: { alerts: Array<{ title: string; level: string; source: string; due_date: string; status: string }> }) {
  if (!alerts.length) return <div style={{ color: '#64748b', fontSize: 12 }}>暂无待办预警</div>
  const levelColors: Record<string, string> = { critical: '#ef4444', high: '#f97316', medium: '#3b82f6', low: '#64748b' }
  return (
    <div className="screen-alert-scroll">
      <div className="screen-alert-scroll__track">
        {[...alerts, ...alerts].map((a, i) => (
          <div className="screen-alert-scroll__item" key={i}>
            <span className="screen-alert-scroll__tag" style={{ background: levelColors[a.level] || '#3b82f6' }}>{a.level}</span>
            <span className="screen-alert-scroll__title">{a.title}</span>
            <span className="screen-alert-scroll__date">{a.due_date || '-'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/** 逾期回款明细表格 */
function OverdueTable({ data }: { data: Array<{ project_name: string; client_name: string; amount: number; overdue_days: number; level: string }> }) {
  if (!data.length) return <div style={{ color: '#64748b', fontSize: 12 }}>无逾期回款</div>
  const levelColors: Record<string, string> = { red: '#ef4444', orange: '#f97316', yellow: '#eab308' }
  return (
    <div className="screen-overdue-table">
      <div className="screen-overdue-table__head">
        <span>项目名</span><span>甲方</span><span>金额(万)</span><span>逾期天数</span><span>级别</span>
      </div>
      <div className="screen-overdue-table__body">
        {data.map((d, i) => (
          <div className="screen-overdue-table__row" key={i}>
            <span>{d.project_name.length > 8 ? d.project_name.slice(0, 8) + '…' : d.project_name}</span>
            <span>{d.client_name.length > 6 ? d.client_name.slice(0, 6) + '…' : d.client_name}</span>
            <span>{(d.amount / 10000).toFixed(1)}</span>
            <span style={{ color: d.overdue_days > 90 ? '#ef4444' : '#f59e0b' }}>{d.overdue_days}天</span>
            <span className="screen-overdue-table__tag" style={{ background: levelColors[d.level] || '#64748b' }}>{d.level}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/** 劳务分班统计 */
function TeamGrid({ data }: { data: Array<{ team: string; count: number; craft: string }> }) {
  if (!data.length) return <div style={{ color: '#64748b', fontSize: 12 }}>暂无数据</div>
  return (
    <div className="screen-team-grid">
      {data.map((t, i) => (
        <div className="screen-team-grid__item" key={i}>
          <div className="screen-team-grid__count">{t.count}</div>
          <div className="screen-team-grid__name">{t.team}</div>
          <div className="screen-team-grid__craft">{t.craft}</div>
        </div>
      ))}
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

      {/* 主内容三栏（对称布局） */}
      <main className="screen-main">
        {/* 左列：项目状态 + 核心健康度 */}
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
                  <RingProgress percent={data.modules.qualification.health_score} size={60} strokeWidth={6}
                    color={data.modules.qualification.expired > 0 ? '#ef4444' : '#22d3ee'} label="资质" />
                  <RingProgress percent={data.modules.document.completeness} size={60} strokeWidth={6}
                    color={data.modules.document.missing > 0 ? '#f97316' : '#22c55e'} label="资料" />
                  <RingProgress percent={Math.max(0, 100 - Math.abs(data.modules.cost.deviation_rate))} size={60} strokeWidth={6}
                    color={data.modules.cost.deviation_rate > 10 ? '#ef4444' : '#3b82f6'} label="成本" />
                  <RingProgress percent={data.modules.bid.win_rate} size={60} strokeWidth={6}
                    color="#8b5cf6" label="中标率" />
                </div>
              </div>
            </div>
          )}

          <div className="screen-card">
            <div className="screen-card__header">
              <span className="screen-card__title">成本结构</span>
            </div>
            <div className="screen-card__body">
              <CostPie data={data.cost_structure || []} />
            </div>
          </div>
        </section>

        {/* 中列：回款趋势 + 项目利润排行 */}
        <section className="screen-panel screen-panel--center">
          <div className="screen-card">
            <div className="screen-card__header">
              <span className="screen-card__title">回款趋势</span>
              <span className="screen-card__badge">近6月 · 计划 vs 实际</span>
            </div>
            <div className="screen-card__body">
              <TrendChart data={data.receivable_trend || []} />
            </div>
          </div>

          <div className="screen-card">
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

        {/* 右列：预警等级 + 预警来源 + 待办滚动 */}
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
                      <div className="screen-source-fill"
                        style={{ width: `${(s.value / Math.max(ov.alert_count, 1)) * 100}%` }} />
                    </div>
                    <span className="screen-source-val">{s.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="screen-card">
            <div className="screen-card__header">
              <span className="screen-card__title">待办预警</span>
              <span className="screen-card__badge">{(data.pending_alerts || []).length} 条待处理</span>
            </div>
            <div className="screen-card__body screen-alert-scroll-wrap">
              <AlertScroll alerts={data.pending_alerts || []} />
            </div>
          </div>
        </section>
      </main>

      {/* 底部横向区域：合同额Top5 + 逾期回款 + 劳务分班 */}
      <section className="screen-bottom-bar">
        <div className="screen-card">
          <div className="screen-card__header">
            <span className="screen-card__title">合同额 Top5</span>
          </div>
          <div className="screen-card__body">
            <ContractTop5Chart data={data.contract_top5 || []} />
          </div>
        </div>
        <div className="screen-card">
          <div className="screen-card__header">
            <span className="screen-card__title">逾期回款</span>
            <span className="screen-card__badge">{(data.overdue_receivables || []).length} 条</span>
          </div>
          <div className="screen-card__body">
            <OverdueTable data={data.overdue_receivables || []} />
          </div>
        </div>
        <div className="screen-card">
          <div className="screen-card__header">
            <span className="screen-card__title">劳务分班</span>
            <span className="screen-card__badge">{(data.labor_team_stats || []).reduce((s, t) => s + t.count, 0)} 人在场</span>
          </div>
          <div className="screen-card__body">
            <TeamGrid data={data.labor_team_stats || []} />
          </div>
        </div>
      </section>

      {/* 底部装饰线 */}
      <div className="screen-footer-line" />
    </div>
  )
}
