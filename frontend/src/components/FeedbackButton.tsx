import { useState } from 'react'
import { Modal, Form, Input, Button, message } from 'antd'
import { CommentOutlined, CloseOutlined } from '@ant-design/icons'
import { createFeedback } from '../api/feedback'

export default function FeedbackButton() {
  const [visible, setVisible] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [hovered, setHovered] = useState(false)
  const [form] = Form.useForm()

  if (!visible) return null

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setLoading(true)
      await createFeedback({
        title: values.title,
        description: values.description || undefined,
        page_url: window.location.pathname,
      })
      message.success('反馈提交成功，感谢您的建议！')
      form.resetFields()
      setModalOpen(false)
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) return
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* Floating button */}
      <div
        style={{
          position: 'fixed',
          right: 24,
          bottom: 24,
          zIndex: 1000,
        }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        <Button
          type="primary"
          shape="circle"
          size="large"
          icon={<CommentOutlined />}
          onClick={() => setModalOpen(true)}
          style={{
            width: 48,
            height: 48,
            fontSize: 20,
            boxShadow: '0 4px 16px rgba(22, 104, 220, 0.35)',
          }}
        />
        {/* Close button - only visible on hover */}
        <Button
          type="text"
          size="small"
          icon={<CloseOutlined />}
          onClick={(e) => {
            e.stopPropagation()
            setVisible(false)
          }}
          style={{
            position: 'absolute',
            top: -8,
            right: -8,
            width: 20,
            height: 20,
            minWidth: 20,
            padding: 0,
            borderRadius: '50%',
            background: '#fff',
            boxShadow: '0 2px 6px rgba(0,0,0,0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 10,
            color: '#999',
            opacity: hovered ? 1 : 0,
            transform: hovered ? 'scale(1)' : 'scale(0.6)',
            transition: 'opacity 0.2s ease, transform 0.2s ease',
            pointerEvents: hovered ? 'auto' : 'none',
          }}
        />
      </div>

      {/* Feedback Modal */}
      <Modal
        title="意见反馈"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={null}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="title"
            label="标题"
            rules={[{ required: true, message: '请输入反馈标题' }]}
          >
            <Input placeholder="请简要描述您的建议或问题" maxLength={200} />
          </Form.Item>
          <Form.Item name="description" label="详细描述">
            <Input.TextArea
              placeholder="可选：补充更多细节"
              rows={4}
              maxLength={2000}
              showCount
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Button onClick={() => setModalOpen(false)} style={{ marginRight: 8 }}>
              取消
            </Button>
            <Button type="primary" loading={loading} onClick={handleSubmit}>
              提交反馈
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
