import React from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
    LayoutDashboard,
    Users,
    History,
    LogOut,
    Shield
} from 'lucide-react';

const SidebarLink = ({ to, icon, label, badge, isActive }) => (
    <NavLink
        to={to}
        className={({ isActive: linkActive }) =>
            `group relative flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-300 overflow-hidden ${isActive || linkActive
                ? 'bg-slate-900 text-white shadow-lg shadow-slate-900/20 border-transparent'
                : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900 border border-transparent'
            }`
        }
    >
        <div className="relative z-10 transition-transform duration-300 group-hover:scale-110">
            {icon}
        </div>
        <span className="relative z-10 font-bold text-sm tracking-tight">{label}</span>
        {badge && (
            <span className={`ml-auto relative z-10 px-2 py-0.5 rounded-lg text-[9px] font-bold uppercase tracking-wider transition-all ${isActive ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-600 group-hover:bg-slate-200'}`}>
                {badge}
            </span>
        )}
    </NavLink>
);

const Sidebar = ({ role, onLogout }) => {
    const navigate = useNavigate();
    const location = useLocation();

    return (
        <aside className="fixed left-0 top-0 h-screen p-6 z-50 w-[290px] hidden lg:block bg-slate-50 border-r border-slate-200">
            <div className="sidebar-inner bg-white border border-slate-200 shadow-2xl shadow-slate-200/50 flex flex-col h-full overflow-hidden rounded-2xl">

                {/* Header with Custom Logo */}
                <div className="px-6 pt-10 pb-8 relative">
                    <div className="flex flex-col items-center justify-center gap-4 relative z-10 text-center">
                        <div className="w-12 h-12 relative">
                            <svg className="w-full h-full drop-shadow-md" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M12 22C12 22 20 18 20 12V5L12 2L4 5V12C4 18 12 22 12 22Z" className="fill-slate-900 stroke-slate-700" strokeWidth="1" />
                                <circle cx="12" cy="14" r="2.5" className="fill-white" />
                                <path d="M12 16.5V18.5" className="stroke-white" strokeWidth="2" strokeLinecap="round" />
                                <path d="M8.5 8C9.5 7 10.5 6.5 12 6.5C13.5 6.5 14.5 7 15.5 8" className="stroke-white/80" strokeWidth="1.5" strokeLinecap="round" />
                                <path d="M7 6.5C8.5 5 10 4.5 12 4.5C14 4.5 15.5 5 17 6.5" className="stroke-white/50" strokeWidth="1.5" strokeLinecap="round" />
                                <path d="M10 9.5C10.5 9 11.25 8.7 12 8.7C12.75 8.7 13.5 9 14 9.5" className="stroke-white" strokeWidth="1.5" strokeLinecap="round" />
                            </svg>
                        </div>
                        <div className="animate-in">
                            <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center justify-center gap-1 leading-none uppercase">
                                SECURE<span className="text-[#FF5F1F]">ALERT</span>
                            </h2>
                        </div>
                    </div>
                    <div className="absolute bottom-0 left-6 right-6 h-px bg-slate-100"></div>
                </div>

                {/* Navigation Content */}
                <nav className="flex-1 px-4 space-y-6 overflow-y-auto overflow-x-hidden custom-scrollbar pb-10 mt-4">
                    {role === 'admin' ? (
                        <>
                            <div className="nav-group space-y-1">
                                <div className="px-5 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Menu</div>
                                <SidebarLink to="/admin/dashboard" icon={<LayoutDashboard size={20} />} label="Overview" />
                                <SidebarLink to="/admin/users" icon={<Users size={20} />} label="Users" />
                                <SidebarLink to="/admin/logs" icon={<History size={20} />} label="System Logs" />
                                <SidebarLink to="/dashboard/apps" icon={<LayoutDashboard size={20} />} label="Apps" />
                            </div>
                        </>
                    ) : (
                        <>
                            <div className="nav-group space-y-1">
                                <div className="px-5 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">My Account</div>
                                <SidebarLink to="/dashboard/overview" icon={<LayoutDashboard size={20} />} label="Overview" />
                                <SidebarLink to="/dashboard/apps" icon={<LayoutDashboard size={20} />} label="My Apps" />
                            </div>
                        </>
                    )}
                </nav>

                <div className="p-4 space-y-1 relative">
                    <div className="absolute top-0 left-6 right-6 h-px bg-slate-100"></div>
                    <div className="pt-2">
                        <button
                            onClick={onLogout}
                            className="w-full flex items-center gap-4 px-4 py-3 rounded-xl text-slate-500 hover:text-red-500 hover:bg-red-50 transition-all group mt-1"
                        >
                            <div className="transition-transform group-hover:translate-x-1">
                                <LogOut size={20} />
                            </div>
                            <span className="font-bold text-sm tracking-tight">Logout</span>
                        </button>
                    </div>
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
