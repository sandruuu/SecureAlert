import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Shield, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

const AdminLogs = () => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('ALL');

    useEffect(() => {
        fetchLogs();
        const interval = setInterval(fetchLogs, 5000);
        return () => clearInterval(interval);
    }, []);

    const fetchLogs = async () => {
        try {
            const res = await axios.get('/api/admin/logs');
            setLogs(res.data);
            setLoading(false);
        } catch (err) {
            console.error("Failed to fetch logs", err);
            setLoading(false);
        }
    };

    const getEventIcon = (action) => {
        if (action === 'BLOCKED' || action === 'SESSION_TERMINATED')
            return <XCircle size={16} className="text-red-500" />;
        if (action === 'MFA_CHALLENGE' || action === 'POSTURE_VIOLATION')
            return <AlertTriangle size={16} className="text-yellow-500" />;
        return <CheckCircle size={16} className="text-green-500" />;
    };

    const getActionLabel = (action) => {
        const labels = {
            'LOGIN_SUCCESS': 'Login Success',
            'BLOCKED': 'Access Blocked',
            'MFA_CHALLENGE': 'MFA Required',
            'POSTURE_OK': 'Posture OK',
            'POSTURE_VIOLATION': 'Posture Violation',
            'SESSION_TERMINATED': 'Session Terminated'
        };
        return labels[action] || action;
    };

    const formatTime = (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });
    };

    const getScoreColor = (score) => {
        if (score === null || score === undefined) return 'text-slate-400';
        if (score > 70) return 'text-green-600 font-bold';
        if (score >= 60) return 'text-yellow-600 font-bold';
        return 'text-red-600 font-bold';
    };

    const getActionBadgeStyle = (action) => {
        if (action === 'BLOCKED' || action === 'SESSION_TERMINATED')
            return 'bg-red-50 text-red-700';
        if (action === 'MFA_CHALLENGE' || action === 'POSTURE_VIOLATION')
            return 'bg-yellow-50 text-yellow-700';
        return 'bg-green-50 text-green-700';
    };

    const filteredLogs = filter === 'ALL'
        ? logs
        : logs.filter(log => log.event_source === filter);

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
            </div>

            {/* Filter Tabs */}
            <div className="flex gap-2">
                {['ALL', 'AUTH', 'POSTURE'].map(f => (
                    <button
                        key={f}
                        onClick={() => setFilter(f)}
                        className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${filter === f
                            ? 'bg-slate-900 text-white shadow-lg shadow-slate-900/20'
                            : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'
                            }`}
                    >
                        {f === 'ALL' ? 'All' : f === 'AUTH' ? 'Authentication' : 'Posture'}
                    </button>
                ))}
            </div>

            {/* Table */}
            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center py-16">
                        <div className="h-8 w-8 border-4 border-slate-200 border-t-slate-900 rounded-full animate-spin"></div>
                    </div>
                ) : filteredLogs.length === 0 ? (
                    <div className="text-center py-16 text-slate-400">
                        <Shield size={40} className="mx-auto mb-3 opacity-50" />
                        <p className="font-medium">No events found</p>
                    </div>
                ) : (
                    <table className="w-full">
                        <thead>
                            <tr className="border-b border-slate-100">
                                <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">Status</th>
                                <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">Time</th>
                                <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">User</th>
                                <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">Action</th>
                                <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">Source</th>
                                <th className="px-6 py-4 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">IP Address</th>
                                <th className="px-6 py-4 text-right text-[10px] font-bold text-slate-400 uppercase tracking-widest">Score</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {filteredLogs.map((log) => (
                                <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                                    <td className="px-6 py-4">
                                        {getEventIcon(log.action)}
                                    </td>
                                    <td className="px-6 py-4 text-sm text-slate-500 whitespace-nowrap">
                                        {formatTime(log.timestamp)}
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="font-bold text-sm text-slate-900">{log.username}</span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={`text-xs font-bold px-2.5 py-1 rounded-lg ${getActionBadgeStyle(log.action)}`}>
                                            {getActionLabel(log.action)}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={`text-xs font-bold px-2 py-1 rounded-lg ${log.event_source === 'POSTURE'
                                            ? 'bg-purple-50 text-purple-700'
                                            : 'bg-blue-50 text-blue-700'
                                            }`}>
                                            {log.event_source}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-sm text-slate-500">
                                        {log.ip_address || '—'}
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <span className={`text-sm ${getScoreColor(log.risk_score)}`}>
                                            {log.risk_score ?? '—'}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Footer */}
            <p className="text-center text-xs text-slate-400">Auto-refreshes every 5 seconds</p>
        </div>
    );
};

export default AdminLogs;
