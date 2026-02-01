import React, { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import { startRegistration } from '@simplewebauthn/browser';
import Sidebar from '../components/Sidebar';
import AdminUsers from './AdminUsers';
import AdminLogs from './AdminLogs';
import { ShieldCheck, Server, Activity, Smartphone } from 'lucide-react';

const AdminOverview = ({ trustScore }) => {
    const [loading, setLoading] = useState(false);

    const handleAddDevice = async () => {
        if (!window.confirm("Do you want to register this current device as a new authentication method?")) return;
        setLoading(true);
        try {
            // 1. Get Options
            const resp = await axios.post('/api/user/devices/register/options');
            // 2. WebAuthn
            const attResp = await startRegistration(resp.data);
            // 3. Verify
            await axios.post('/api/user/devices/register/verify', {
                // Admin username is not passed as prop to Overview, but cookie handles auth. 
                // The verify endpoint gets username from session, so we don't strictly need it in body if backend relies on session.
                // However, UserDashboard sent { username, response }.
                // Let's check main.py verify endpoint again.
                // main.py line 529: username = sessions[session_id]["username"]
                // It doesn't use req.username! So we are safe sending just response or dummy username.
                response: attResp
            });
            alert("Device Registered Successfully! You can now use this device to login.");
        } catch (err) {
            console.error(err);
            alert(err.response?.data?.detail || err.message || "Device Registration Failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div>
                <h1 className="text-2xl font-bold text-slate-900">Admin Overview</h1>
                <p className="text-slate-500">System status and personal security score</p>
            </div>

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

                {/* Resources Card */}
                <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4 hover:border-slate-900 transition-colors cursor-pointer group" onClick={() => window.location.href = "/"}>
                    <div className="p-4 rounded-xl bg-blue-50 text-blue-600 group-hover:bg-blue-100 transition-colors">
                        <Server size={32} />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Web Resources</h3>
                        <div className="text-sm font-bold text-slate-900">Access Portal</div>
                    </div>
                </div>
            </div>
        </div>
    );
};


const AdminDashboard = ({ trustScore, onLogout }) => {
    return (
        <div className="flex h-screen bg-slate-50 font-sans overflow-hidden">
            <Sidebar role="admin" onLogout={onLogout} />
            <main className="flex-1 overflow-y-auto h-screen p-8 lg:ml-[290px]">
                <div className="max-w-6xl mx-auto">
                    <Routes>
                        <Route path="/" element={<Navigate to="dashboard" replace />} />
                        <Route path="dashboard" element={<AdminOverview trustScore={trustScore} />} />
                        <Route path="users" element={<AdminUsers />} />
                        <Route path="logs" element={<AdminLogs />} />
                    </Routes>
                </div>
            </main>
        </div>
    );
};

export default AdminDashboard;
