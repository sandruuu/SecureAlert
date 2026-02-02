import { useState } from 'react'
import axios from 'axios'
import { startRegistration } from '@simplewebauthn/browser'
import { ShieldCheck, Server, Smartphone, Terminal, Copy, Check } from 'lucide-react'
import { useNavigate, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import UserApplications from './UserApplications'
import SetupAuthenticator from '../components/SetupAuthenticator'

const UserOverview = ({ username, trustScore, enrollmentToken, onLogout }) => {
    const [loading, setLoading] = useState(false)
    const [vpnConfig, setVpnConfig] = useState(null)
    const [error, setError] = useState('')
    const [copied, setCopied] = useState(false)
    const navigate = useNavigate()

    const handleProvisionVPN = async () => {
        setLoading(true)
        setError('')
        try {
            const resp = await axios.post('/api/vpn/provision')
            setVpnConfig(resp.data)
        } catch (err) { setError(err.message) } finally { setLoading(false) }
    }

    const handleAddDevice = async () => {
        if (!window.confirm("Do you want to register this current device as a new authentication method?")) return;
        setLoading(true)
        setError('')
        try {
            // 1. Get Options
            const resp = await axios.post('/api/user/devices/register/options')
            // 2. WebAuthn
            const attResp = await startRegistration(resp.data)
            // 3. Verify
            await axios.post('/api/user/devices/register/verify', { username, response: attResp })
            alert("Device Registered Successfully! You can now use this device to login.")
        } catch (err) {
            console.error(err);
            setError(err.response?.data?.detail || err.message || "Device Registration Failed")
        } finally {
            setLoading(false)
        }
    }

    // Helper for Score Color
    const getScoreColor = (sc) => {
        if (sc >= 90) return 'text-green-700 bg-green-50 border-green-200';
        if (sc >= 50) return 'text-yellow-700 bg-yellow-50 border-yellow-200';
        return 'text-red-700 bg-red-50 border-red-200';
    }

    const copyCommand = () => {
        const cmd = `.\\posture_agent.ps1 -EnrollToken "${enrollmentToken}"`
        navigator.clipboard.writeText(cmd)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div>
                <h1 className="text-2xl font-bold text-slate-900">Welcome, {username}</h1>
                <p className="text-slate-500">Manage your access and devices</p>
            </div>

            {error && (
                <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm border border-red-100">
                    {error}
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Trust Score Card */}
                <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
                    <div className={`p-4 rounded-xl ${trustScore >= 90 ? 'bg-green-100 text-green-600' : 'bg-yellow-100 text-yellow-600'}`}>
                        <ShieldCheck size={32} />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">My Trust Score</h3>
                        <div className="text-3xl font-bold text-slate-900">{trustScore}/100</div>
                    </div>
                </div>
            </div>
        </div>
    )
}

const UserDashboard = ({ username, trustScore, role, enrollmentToken, onLogout }) => {
    return (
        <div className="flex h-screen bg-slate-50 font-sans overflow-hidden">
            <Sidebar role={role} onLogout={onLogout} />
            <main className="flex-1 overflow-y-auto h-screen p-8 lg:ml-[290px]">
                <div className="max-w-6xl mx-auto">
                    <Routes>
                        <Route path="/" element={<Navigate to="overview" replace />} />
                        <Route path="overview" element={<UserOverview username={username} trustScore={trustScore} enrollmentToken={enrollmentToken} onLogout={onLogout} />} />
                        <Route path="apps" element={<UserApplications />} />
                    </Routes>
                </div>
            </main>
        </div>
    )
}

export default UserDashboard
