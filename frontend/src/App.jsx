import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import AppLayout from './components/AppLayout'
import LoginPage from './pages/LoginPage'
import HomePage from './pages/HomePage'
import NewReportPage from './pages/NewReportPage'
import ReportDetailPage from './pages/ReportDetailPage'
import MyReportsPage from './pages/MyReportsPage'
import AuthorityDashboard from './pages/AuthorityDashboard'
import AdminDashboard from './pages/AdminDashboard'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected — all logged-in users */}
        <Route path="/" element={
          <ProtectedRoute>
            <AppLayout><HomePage /></AppLayout>
          </ProtectedRoute>
        } />
        <Route path="/report/new" element={
          <ProtectedRoute>
            <AppLayout><NewReportPage /></AppLayout>
          </ProtectedRoute>
        } />
        <Route path="/reports/:id" element={
          <ProtectedRoute>
            <AppLayout><ReportDetailPage /></AppLayout>
          </ProtectedRoute>
        } />
        <Route path="/my-reports" element={
          <ProtectedRoute>
            <AppLayout><MyReportsPage /></AppLayout>
          </ProtectedRoute>
        } />

        {/* Authority only */}
        <Route path="/authority" element={
          <ProtectedRoute roles={['authority', 'admin']}>
            <AppLayout><AuthorityDashboard /></AppLayout>
          </ProtectedRoute>
        } />

        {/* Admin only */}
        <Route path="/admin" element={
          <ProtectedRoute roles={['admin']}>
            <AppLayout><AdminDashboard /></AppLayout>
          </ProtectedRoute>
        } />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
