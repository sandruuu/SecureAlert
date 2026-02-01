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

            {/* Agent Enrollment Banner */}
            {enrollmentToken && (
                <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 animate-in slide-in-from-top-2">
                    <div className="flex items-start gap-4">
                        <div className="p-3 rounded-xl bg-amber-100 text-amber-600">
                            <Terminal size={24} />
                        </div>
                        <div className="flex-1 min-w-0">
                            <h3 className="font-bold text-amber-900">Posture Agent Required</h3>
                            <p className="text-sm text-amber-700 mt-1">
                                To ensure secure access, please run the posture agent on this device.
                            </p>
                            <div className="mt-4 bg-slate-900 rounded-xl p-4 relative group">
                                <code className="text-xs text-green-400 font-mono break-all">
                                    .\posture_agent.ps1 -EnrollToken "{enrollmentToken}"
                                </code>
                                <button
                                    onClick={copyCommand}
                                    className="absolute top-2 right-2 p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
                                    title="Copy command"
                                >
                                    {copied ? <Check size={16} className="text-green-400" /> : <Copy size={16} />}
                                </button>
                            </div>
                            <p className="text-xs text-amber-600 mt-3">
                                Open PowerShell in your project folder and paste this command.
                            </p>
                        </div>
                    </div>
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

                {/* Add Device Card */}
                <button onClick={handleAddDevice} disabled={loading} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4 hover:border-slate-900 transition-colors cursor-pointer group text-left">
                    <div className="p-4 rounded-xl bg-purple-50 text-purple-600 group-hover:bg-purple-100 transition-colors">
                        <Smartphone size={32} />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">{loading ? 'Processing...' : 'Add Device'}</h3>
                        <div className="text-sm font-bold text-slate-900">Register New Key</div>
                    </div>
                </button>

                {/* VPN Card */}
                <button onClick={handleProvisionVPN} disabled={loading} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4 hover:border-slate-900 transition-colors cursor-pointer group text-left">
                    <div className="p-4 rounded-xl bg-orange-50 text-orange-600 group-hover:bg-orange-100 transition-colors">
                        <ShieldCheck size={32} />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">{loading ? 'Setting up...' : 'Secure VPN'}</h3>
                        <div className="text-sm font-bold text-slate-900">Get Config</div>
                    </div>
                </button>
            </div>

            {/* VPN Display Logic */}
            {vpnConfig && (
                <div className="bg-slate-900 text-white p-6 rounded-xl relative overflow-hidden mb-6 animate-in slide-in-from-top-2">
                    <h3 className="font-bold mb-4">VPN Configuration</h3>
                    <div className="flex flex-col md:flex-row gap-6 items-center">
                        <div className="bg-white p-2 rounded-lg shrink-0">
                            <img src={vpnConfig.qr_code} alt="VPN QR" className="w-[120px] h-[120px]" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm text-slate-300 mb-2">1. Install WireGuard</p>
                            <p className="text-sm text-slate-300 mb-4">2. Scan QR or use config:</p>
                            <textarea
                                value={vpnConfig.config}
                                readOnly
                                className="w-full h-[80px] bg-slate-800 rounded-lg p-3 text-[10px] font-mono text-slate-400 focus:outline-none"
                            />
                        </div>
                    </div>
                </div>
            )}
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
