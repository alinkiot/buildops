import { useState } from 'react'
import { Button, Form, Input, Typography, message } from 'antd'
import { LockOutlined, UserOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const features = [
  '经营驾驶舱 · 全局风险一屏掌控',
  '项目 / 资质 / 资料 / 成本全流程在线',
  '财税·回款·劳务·招投标多维联动预警',
]

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      await login(values.username, values.password)
      message.success('登录成功')
      navigate('/dashboard')
    } catch {
      // 错误已在拦截器提示
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', background: '#0b1f3a' }}>
      {/* 左侧品牌区 */}
      <div
        style={{
          flex: 1.1,
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '0 8%',
          color: '#fff',
          overflow: 'hidden',
          background:
            'radial-gradient(1200px 600px at 10% 10%, rgba(22,104,220,0.55), transparent 60%), radial-gradient(900px 500px at 90% 90%, rgba(19,194,194,0.35), transparent 55%), linear-gradient(135deg, #0b1f3a 0%, #0b3d91 100%)',
        }}
      >
        {/* 装饰网格 */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundImage:
              'linear-gradient(rgba(255,255,255,0.045) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.045) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
            maskImage: 'radial-gradient(circle at 30% 40%, #000 0%, transparent 75%)',
          }}
        />
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 40 }}>
            <div
              style={{
                width: 52,
                height: 52,
                borderRadius: 14,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'linear-gradient(135deg, #1668dc 0%, #13c2c2 100%)',
                boxShadow: '0 8px 24px rgba(22,104,220,0.5)',
                fontSize: 26,
              }}
            >
              <SafetyCertificateOutlined />
            </div>
            <div>
              <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: 1 }}>施工企业智能运营</div>
              <div style={{ fontSize: 12, letterSpacing: 4, opacity: 0.6 }}>DIGITAL OPERATION PLATFORM</div>
            </div>
          </div>

          <Typography.Title level={1} style={{ color: '#fff', fontWeight: 800, lineHeight: 1.2, margin: 0, fontSize: 40 }}>
            全流程智能托管
            <br />
            <span className="brand-gradient-text">数字化管理平台</span>
          </Typography.Title>
          <Typography.Paragraph style={{ color: 'rgba(255,255,255,0.7)', fontSize: 15, marginTop: 18, maxWidth: 460 }}>
            从项目立项到回款清欠，贯穿经营全链路，用数据驱动决策，让每一个施工企业稳健经营。
          </Typography.Paragraph>

          <div style={{ marginTop: 36, display: 'flex', flexDirection: 'column', gap: 14 }}>
            {features.map((f) => (
              <div key={f} style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'rgba(255,255,255,0.88)', fontSize: 14 }}>
                <span
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: '50%',
                    background: 'rgba(255,255,255,0.12)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 12,
                    color: '#7ee0e0',
                  }}
                >
                  ✓
                </span>
                {f}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 右侧登录区 */}
      <div
        style={{
          width: 480,
          minWidth: 380,
          background: '#fff',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '0 56px',
        }}
      >
        <div style={{ marginBottom: 32 }}>
          <Typography.Title level={3} style={{ marginBottom: 6 }}>
            欢迎登录
          </Typography.Title>
        </div>

        <Form
          form={form}
          onFinish={onFinish}
          size="large"
          layout="vertical"
          initialValues={{ username: '', password: '' }}
        >
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined style={{ color: '#94a3b8' }} />} placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined style={{ color: '#94a3b8' }} />} placeholder="请输入密码" />
          </Form.Item>
          <Form.Item style={{ marginTop: 28 }}>
            <Button
              type="primary"
              htmlType="submit"
              block
              loading={loading}
              style={{ height: 46, fontSize: 16, fontWeight: 600 }}
            >
              登 录
            </Button>
          </Form.Item>
        </Form>

        <div style={{ marginTop: 40, fontSize: 12, color: '#cbd5e1', textAlign: 'center' }}>
          © {new Date().getFullYear()} 施工企业运营托管数字化系统
        </div>
      </div>
    </div>
  )
}
