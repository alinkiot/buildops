import { useEffect, useState } from 'react'
import { Card, Col, Row, Statistic, Table, Tag, Progress, Spin, Empty, Button } from 'antd'
import {
  ProjectOutlined,
  DollarOutlined,
  RiseOutlined,
  AlertOutlined,
  RightOutlined,
} from '@ant-design/icons'
import http from '../api/client'
import type { ApiResponse, DashboardData } from '../api/types'
import { ALERT_LEVEL, ALERT_SOURCE, fmtMoney } from '../constants'
import { useNavigate } from 'react-router-dom'

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    http
      .get<ApiResponse<DashboardData>>('/dashboard')
      .then(({ data }) => setData(data.data))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Spin />
  if (!data) return <Empty />

  const ov = data.overview
  const maxProfit = Math.max(...data.project_profit_rank.map((p) => Math.abs(p.profit)), 1)

  const cards = [
    { title: '在建项目', value: ov.ongoing_count, suffix: `/ ${ov.project_count} 个`, icon: <ProjectOutlined />, gradient: 'linear-gradient(135deg, #1668dc 0%, #0b3d91 100%)' },
    { title: '合同总额', value: fmtMoney(ov.contract_amount), icon: <DollarOutlined />, gradient: 'linear-gradient(135deg, #0ea5b7 0%, #0e7490 100%)' },
    { title: '累计回款', value: fmtMoney(ov.received_amount), icon: <DollarOutlined />, gradient: 'linear-gradient(135deg, #22c55e 0%, #15803d 100%)' },
    { title: '毛利(回款-成本)', value: fmtMoney(ov.profit_amount), icon: <RiseOutlined />, gradient: 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)' },
    { title: '待回款', value: fmtMoney(ov.receivable_amount), icon: <DollarOutlined />, gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' },
    { title: '待处理预警', value: ov.pending_alert_count, suffix: `/ ${ov.alert_count} 条`, icon: <AlertOutlined />, gradient: 'linear-gradient(135deg, #f43f5e 0%, #be123c 100%)' },
  ]

  return (
    <div>
      <div className="page-title" style={{ marginBottom: 16 }}>经营驾驶舱</div>
      <Row gutter={[16, 16]}>
        {cards.map((c) => (
          <Col xs={12} sm={8} lg={4} key={c.title}>
            <Card className="kpi-card" size="small" style={{ background: c.gradient }} styles={{ body: { padding: 18 } }}>
              <div className="kpi-title">{c.icon} {c.title}</div>
              <div className="kpi-value">
                {c.value}
                {c.suffix && <span className="kpi-suffix">{c.suffix}</span>}
              </div>
              <span className="kpi-icon">{c.icon}</span>
            </Card>
          </Col>
        ))}
      </Row>

      {data.modules && (
        <>
          <div className="page-title" style={{ margin: '24px 0 12px', fontSize: 15 }}>模块经营概览</div>
          <Row gutter={[16, 16]} align="stretch" className="eq-grid">
            <Col xs={24} sm={12} lg={8} xl={6}>
              <Card size="small" hoverable className="module-card" title="资质健康度">
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Progress type="circle" size={64} percent={data.modules.qualification.health_score}
                    status={data.modules.qualification.expired > 0 ? 'exception' : 'normal'} />
                  <div style={{ fontSize: 13, color: '#666' }}>
                    <div>有效 {data.modules.qualification.valid}</div>
                    <div style={{ color: '#fa8c16' }}>临期 {data.modules.qualification.expiring}</div>
                    <div style={{ color: '#f5222d' }}>过期 {data.modules.qualification.expired}</div>
                  </div>
                </div>
                <Button className="card-detail-btn" type="link" size="small" onClick={() => navigate('/qualifications')}>详情 <RightOutlined /></Button>
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={8} xl={6}>
              <Card size="small" hoverable className="module-card" title="资料完整度">
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Progress type="circle" size={64} percent={data.modules.document.completeness}
                    status={data.modules.document.missing > 0 ? 'exception' : 'normal'} />
                  <div style={{ fontSize: 13, color: '#666' }}>
                    <div>已通过 {data.modules.document.approved}</div>
                    <div>应交 {data.modules.document.required_total}</div>
                    <div style={{ color: '#f5222d' }}>缺项 {data.modules.document.missing}</div>
                  </div>
                </div>
                <Button className="card-detail-btn" type="link" size="small" onClick={() => navigate('/documents')}>详情 <RightOutlined /></Button>
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={8} xl={6}>
              <Card size="small" hoverable className="module-card" title="成本偏差">
                <Statistic value={data.modules.cost.deviation_rate} suffix="%" precision={1}
                  valueStyle={{ color: data.modules.cost.deviation_rate > 0 ? '#f5222d' : '#52c41a', fontSize: 22 }} />
                <div style={{ fontSize: 12, color: '#999' }}>
                  预算 {fmtMoney(data.modules.cost.total_budget)} / 已发生 {fmtMoney(data.modules.cost.total_actual)}
                </div>
                <div style={{ fontSize: 12, color: '#fa8c16' }}>
                  超预算项目 {data.modules.cost.over_budget_projects} · 待审批 {data.modules.cost.pending_approval}
                </div>
                <Button className="card-detail-btn" type="link" size="small" onClick={() => navigate('/costs')}>详情 <RightOutlined /></Button>
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={8} xl={6}>
              <Card size="small" hoverable className="module-card" title="财税净利润">
                <Statistic value={fmtMoney(data.modules.finance.net_profit)} valueStyle={{ color: '#722ed1', fontSize: 22 }} />
                <div style={{ fontSize: 12, color: '#999' }}>
                  收入 {fmtMoney(data.modules.finance.total_income)} · 税费 {fmtMoney(data.modules.finance.total_tax)}
                </div>
                <div style={{ fontSize: 12, color: data.modules.finance.no_invoice_ratio > 10 ? '#f5222d' : '#999' }}>
                  无票占比 {data.modules.finance.no_invoice_ratio}%
                </div>
                <Button className="card-detail-btn" type="link" size="small" onClick={() => navigate('/finance')}>详情 <RightOutlined /></Button>
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={8} xl={6}>
              <Card size="small" hoverable className="module-card" title="回款分级">
                <Statistic value={fmtMoney(data.modules.receivable.total_outstanding)} valueStyle={{ fontSize: 22, color: '#fa8c16' }} />
                <div style={{ fontSize: 12, color: '#999' }}>待回款 · 逾期未收 {fmtMoney(data.modules.receivable.overdue_outstanding)}</div>
                <div style={{ fontSize: 12 }}>
                  <Tag color="orange">逾期 {data.modules.receivable.overdue}</Tag>
                  <Tag color="volcano">呆滞 {data.modules.receivable.stagnant}</Tag>
                  <Tag color="red">坏账 {data.modules.receivable.bad_debt_risk}</Tag>
                </div>
                {data.modules.receivable.worst_client && (
                  <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                    最差甲方：{data.modules.receivable.worst_client}（{data.modules.receivable.worst_client_level} 级）
                  </div>
                )}
                <Button className="card-detail-btn" type="link" size="small" onClick={() => navigate('/receivables')}>详情 <RightOutlined /></Button>
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={8} xl={6}>
              <Card size="small" hoverable className="module-card" title="招投标">
                <Statistic value={data.modules.bid.win_rate} suffix="% 中标率" valueStyle={{ color: '#1677ff', fontSize: 22 }} />
                <div style={{ fontSize: 12, color: '#999' }}>
                  标的 {data.modules.bid.total} · 有效投标 {data.modules.bid.bidded} · 已中标 {data.modules.bid.won}
                </div>
                <div style={{ fontSize: 12, color: data.modules.bid.deposit_overdue > 0 ? '#f5222d' : '#999' }}>
                  未退保证金 {fmtMoney(data.modules.bid.deposit_outstanding)} · 逾期 {data.modules.bid.deposit_overdue} 笔
                </div>
                <Button className="card-detail-btn" type="link" size="small" onClick={() => navigate('/tenders')}>详情 <RightOutlined /></Button>
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={8} xl={6}>
              <Card size="small" hoverable className="module-card" title="劳务用工">
                <Statistic value={data.modules.labor.onsite} suffix="人在场" valueStyle={{ fontSize: 22 }} />
                <div style={{ fontSize: 12 }}>
                  <Tag color={data.modules.labor.contract_missing > 0 ? 'red' : 'default'}>无合同 {data.modules.labor.contract_missing}</Tag>
                  <Tag color={data.modules.labor.insurance_missing > 0 ? 'red' : 'default'}>保险缺失 {data.modules.labor.insurance_missing}</Tag>
                </div>
                <div style={{ fontSize: 12, color: '#fa8c16' }}>待发工资 {fmtMoney(data.modules.labor.unpaid_amount)}</div>
                <Button className="card-detail-btn" type="link" size="small" onClick={() => navigate('/labor')}>详情 <RightOutlined /></Button>
              </Card>
            </Col>
          </Row>
        </>
      )}

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="项目利润排行（回款 - 成本）" size="small">
            <Table
              rowKey="id"
              size="small"
              pagination={false}
              dataSource={data.project_profit_rank}
              columns={[
                { title: '项目', dataIndex: 'name', ellipsis: true },
                { title: '合同额', dataIndex: 'contract_amount', render: fmtMoney, width: 110 },
                { title: '待回款', dataIndex: 'receivable', render: fmtMoney, width: 110 },
                {
                  title: '毛利',
                  dataIndex: 'profit',
                  width: 200,
                  render: (v: number) => (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Progress
                        percent={Math.round((Math.abs(v) / maxProfit) * 100)}
                        showInfo={false}
                        strokeColor={v >= 0 ? '#52c41a' : '#f5222d'}
                        style={{ width: 100, margin: 0 }}
                      />
                      <span style={{ color: v >= 0 ? '#52c41a' : '#f5222d' }}>{fmtMoney(v)}</span>
                    </div>
                  ),
                },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="预警分布（按来源）" size="small" style={{ marginBottom: 16 }}>
            {data.alert_by_source.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              data.alert_by_source.map((s) => (
                <div key={s.name} style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>{s.name}</span>
                    <span>{s.value} 条</span>
                  </div>
                  <Progress percent={Math.round((s.value / ov.alert_count) * 100)} showInfo={false} />
                </div>
              ))
            )}
          </Card>
          <Card title="预警等级" size="small">
            {data.alert_by_level.map((l) => {
              const key = Object.keys(ALERT_LEVEL).find((k) => ALERT_LEVEL[k].label === l.name)
              return (
                <Tag key={l.name} color={key ? ALERT_LEVEL[key].color : 'default'} style={{ marginBottom: 8 }}>
                  {l.name}：{l.value} 条
                </Tag>
              )
            })}
            <div style={{ marginTop: 12, color: '#999', fontSize: 12 }}>
              来源涵盖：{Object.values(ALERT_SOURCE).join(' / ')}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
