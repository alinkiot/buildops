import { Spin } from 'antd'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import MainLayout from './components/MainLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import DashboardScreen from './pages/DashboardScreen'
import Projects from './pages/Projects'
import Tenders from './pages/Tenders'
import Files from './pages/Files'
import Alerts from './pages/Alerts'
import Qualifications from './pages/Qualifications'
import Documents from './pages/Documents'
import Costs from './pages/Costs'
import Finance from './pages/Finance'
import Receivables from './pages/Receivables'
import Labor from './pages/Labor'
import SystemUsers from './pages/SystemUsers'
import SystemIntegrations from './pages/SystemIntegrations'
import SystemAudit from './pages/SystemAudit'

function RequireAuth({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/screen"
          element={
            <RequireAuth>
              <DashboardScreen />
            </RequireAuth>
          }
        />
        <Route
          path="/"
          element={
            <RequireAuth>
              <MainLayout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="projects" element={<Projects />} />
          <Route path="tenders" element={<Tenders />} />
          <Route path="files" element={<Files />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="system" element={<Navigate to="/system/users" replace />} />
          <Route path="system/users" element={<SystemUsers />} />
          <Route path="system/integrations" element={<SystemIntegrations />} />
          <Route path="system/audit" element={<SystemAudit />} />
          <Route path="qualifications" element={<Qualifications />} />
          <Route path="documents" element={<Documents />} />
          <Route path="costs" element={<Costs />} />
          <Route path="finance" element={<Finance />} />
          <Route path="receivables" element={<Receivables />} />
          <Route path="labor" element={<Labor />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
