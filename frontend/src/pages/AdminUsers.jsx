import { useState, useEffect } from 'react'
import axios from 'axios'
import {
    Search,
    UserPlus,
    CheckCircle,
    RefreshCw,
    Ban,
    Trash2,
    Fingerprint
} from 'lucide-react'

const AdminUsers = () => {
    const [userList, setUserList] = useState([])
    const [searchTerm, setSearchTerm] = useState('')
    const [newUser, setNewUser] = useState({ username: '', full_name: '', role: 'user' })
    const [createdCode, setCreatedCode] = useState('')

    useEffect(() => {
        fetchUsers()
    }, [])

    const fetchUsers = async () => {
        try {
            const resp = await axios.get('/api/admin/users')
            setUserList(resp.data)
        } catch (e) { }
    }

    const handleCreateUser = async (e) => {
        e.preventDefault()
        try {
            const resp = await axios.post('/api/admin/users', newUser)
            setCreatedCode(resp.data.invite_code)
            fetchUsers()
        } catch (err) { alert(err.response?.data?.detail) }
    }

    const handleDeleteUser = async (id) => {
        if (!id) {
            alert("Error: User ID is missing!");
            console.error("Attempted to delete user with missing ID");
            return;
        }
        if (!window.confirm(`Are you sure you want to delete user ${id}? This cannot be undone.`)) return;
        try {
            console.log("Deleting user with ID:", id);
            await axios.delete(`/api/admin/users/${id}`)
            fetchUsers()
        } catch (err) {
            console.error("Delete failed:", err);
            alert(err.response?.data?.detail || "Delete failed")
        }
    }

    const handleToggleStatus = async (id, currentStatus) => {
        try {
            await axios.patch(`/api/admin/users/${id}/status`, { is_active: !currentStatus })
            fetchUsers()
        } catch (err) { alert(err.response?.data?.detail) }
    }

    const handleResetInvite = async (id, username) => {
        if (!window.confirm(`Revoke old invite and generate new one for ${username}?`)) return;
        try {
            const resp = await axios.post(`/api/admin/users/${id}/reset-invite`)
            setCreatedCode(resp.data.invite_code)
            setNewUser(prev => ({ ...prev, username }))
            alert(`New Invite Code for ${username}: ${resp.data.invite_code}`)
        } catch (err) { alert(err.response?.data?.detail) }
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div>
            </div>

            {/* Create User Section */}
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-4 flex items-center gap-2">
                    <UserPlus size={16} /> Invite New User
                </h3>
                <form onSubmit={handleCreateUser} className="flex flex-col md:flex-row gap-4 items-end">
                    <div className="flex-1 w-full space-y-1">
                        <label className="text-xs font-semibold text-slate-600">Email Address</label>
                        <input required placeholder="e.g. ion.popescu@company.com" className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:border-purple-500 focus:ring-2 focus:ring-purple-500/10 outline-none transition-all" value={newUser.username} onChange={e => setNewUser({ ...newUser, username: e.target.value })} />
                    </div>
                    <div className="flex-1 w-full space-y-1">
                        <label className="text-xs font-semibold text-slate-600">Full Name</label>
                        <input required placeholder="e.g. Ion Popescu" className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:border-purple-500 outline-none transition-all" value={newUser.full_name} onChange={e => setNewUser({ ...newUser, full_name: e.target.value })} />
                    </div>
                    <div className="w-full md:w-32 space-y-1">
                        <label className="text-xs font-semibold text-slate-600">Role</label>
                        <select className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg outline-none" value={newUser.role} onChange={e => setNewUser({ ...newUser, role: e.target.value })}>
                            <option value="user">User</option>
                            <option value="admin">Admin</option>
                        </select>
                    </div>
                    <button type="submit" className="w-full md:w-auto bg-orange-300 text-white font-semibold py-2.5 px-6 rounded-lg transition-all shadow-lg shadow-purple-600/20 active:scale-95 flex items-center justify-center gap-2">
                        Generate
                    </button>
                </form>

                {createdCode && (
                    <div className="mt-6 p-4 bg-green-50 border border-green-100 rounded-xl flex items-center gap-3 animate-in slide-in-from-top-2">
                        <div className="p-2 bg-green-100 rounded-full text-green-600">
                            <CheckCircle size={20} />
                        </div>
                        <div>
                            <p className="text-sm text-green-800 font-medium">Invitation Sent for <span className="font-bold">{newUser.username}</span></p>
                            <p className="text-xs text-green-600">The user has received an email with instructions.</p>
                        </div>
                    </div>
                )}
            </div>

            {/* User List Section */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="p-4 border-b border-slate-100 flex flex-col md:flex-row justify-between items-center gap-4 bg-white">
                    <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Existing Users</h3>
                    <div className="relative w-full md:w-64">
                        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search users..."
                            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-slate-400 transition-colors"
                            value={searchTerm}
                            onChange={e => setSearchTerm(e.target.value)}
                        />
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-slate-50/50 text-xs uppercase text-slate-500 font-semibold border-b border-slate-100">
                                <th className="p-4">User</th>
                                <th className="p-4">Role</th>
                                <th className="p-4">Status</th>
                                <th className="p-4 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="text-sm">
                            {userList.filter(u => u.username.includes(searchTerm) || (u.full_name && u.full_name.includes(searchTerm))).map(u => (
                                <tr key={u.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors group">
                                    <td className="p-4">
                                        <div className="font-semibold text-slate-900">{u.username}</div>
                                        <div className="text-xs text-slate-500">{u.full_name || 'No Name'}</div>
                                    </td>
                                    <td className="p-4">
                                        <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wide border ${u.role === 'admin' ? 'bg-purple-50 text-purple-700 border-purple-200' : 'bg-slate-100 text-slate-600 border-slate-200'}`}>
                                            {u.role}
                                        </span>
                                    </td>
                                    <td className="p-4">
                                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${u.is_active ? 'bg-green-50 text-green-700 border-green-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>
                                            <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-green-500' : 'bg-amber-500'}`}></span>
                                            {u.is_active ? 'Active' : 'Pending'}
                                        </span>
                                    </td>
                                    <td className="p-4 text-right">
                                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            {!u.is_active && (
                                                <button title="Regenerate Invite" onClick={() => handleResetInvite(u.id, u.username)} className="p-2 hover:bg-blue-50 text-slate-400 hover:text-blue-600 rounded-lg transition-colors">
                                                    <RefreshCw size={16} />
                                                </button>
                                            )}
                                            <button title={u.is_active ? "Suspend User" : "Activate User"} onClick={() => handleToggleStatus(u.id, u.is_active)} className={`p-2 rounded-lg transition-colors ${u.is_active ? 'hover:bg-amber-50 text-slate-400 hover:text-amber-600' : 'hover:bg-green-50 text-slate-400 hover:text-green-600'}`}>
                                                {u.is_active ? <Ban size={16} /> : <CheckCircle size={16} />}
                                            </button>
                                            <button title="Delete User" onClick={() => handleDeleteUser(u.id)} className="p-2 hover:bg-red-50 text-slate-400 hover:text-red-600 rounded-lg transition-colors">
                                                <Trash2 size={16} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {userList.length === 0 && (
                        <div className="p-8 text-center text-slate-500">No users found.</div>
                    )}
                </div>
            </div>
        </div>
    )
}

export default AdminUsers
