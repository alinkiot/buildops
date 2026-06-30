import { useEffect, useState } from 'react'
import {
  Table, Tag, Space, Button, Modal, Form, Input, message, Card, Row, Col, Upload, Descriptions,
} from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import http, { tokenStore } from '../api/client'
import type { ApiResponse, PageResult } from '../api/types'

interface IntegrationLogRow {
  id: number; channel: string; provider: string; action: string; target?: string
  status: string; response_summary?: string; operator_name?: string; created_at: string
}

const CHANNEL_LABEL: Record<string, string> = { sms: '短信', esign: '电子签', ocr: 'OCR' }

export default function SystemIntegrations() {
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
