import { useState, useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import axios from 'axios'
import LoginPage from './pages/LoginPage'
import UserDashboard from './pages/UserDashboard'
import AdminDashboard from './pages/AdminDashboard'
import AdminLogs from './pages/AdminLogs'
import './index.css'

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const resp = await axios.get('/api/auth')
        if (resp.data.username) {
          setUser({
            username: resp.data.username,
            role: resp.data.role || 'user',
            score: resp.data.trust_score || 0
          })
        }
      } catch (e) {
        // Not logged in
        setUser(null)
      } finally {
        setLoading(false)
      }
    }
    checkAuth()
  }, [])

  const handleLoginSuccess = (userData) => {
    setUser({
      username: userData.username,
      role: userData.role || 'user',
      score: userData.score || 0,
      enrollmentToken: userData.enrollment_token || null,
      agentRequired: userData.agent_required || false
    })
    // Navigation is handled by the Routes redirect logic or explicity here?
    // Routes logic will auto-redirect because 'user' state changes.
  }

  const handleLogout = async () => {
    try { await axios.post('/api/logout') } catch (e) { }
    setUser(null)
    navigate('/login')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 border-4 border-slate-200 border-t-purple-600 rounded-full animate-spin"></div>
          <div className="text-sm font-semibold text-slate-500">Loading SecureAlert...</div>
        </div>
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={
        !user ? (
          <LoginPage onLoginSuccess={handleLoginSuccess} />
        ) : (
          <Navigate to={user.role === 'admin' ? "/admin/dashboard" : "/dashboard"} replace />
        )
      } />

      <Route path="/admin/*" element={
        user && user.role === 'admin' ? (
          <AdminDashboard trustScore={user.score} onLogout={handleLogout} />
        ) : (
          <Navigate to={user ? "/dashboard" : "/login"} replace />
        )
      } />


      <Route path="/dashboard/*" element={
        user ? (
          <UserDashboard
            username={user.username}
            role={user.role}
            trustScore={user.score}
            enrollmentToken={user.enrollmentToken}
            agentRequired={user.agentRequired}
            onLogout={handleLogout}
          />
        ) : (
          <Navigate to="/login" replace />
        )
      } />

      {/* Catch-all redirect */}
      <Route path="*" element={<Navigate to={user ? (user.role === 'admin' ? "/admin/dashboard" : "/dashboard") : "/login"} replace />} />
    </Routes>
  )
}

export default App
