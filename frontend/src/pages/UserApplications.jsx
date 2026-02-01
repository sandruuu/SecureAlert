import React from 'react';
import { Server, ExternalLink } from 'lucide-react';

const UserApplications = () => {
    const apps = [
        {
            id: 1,
            name: 'Secure Storage',
            description: 'Access the internal encrypted file storage.',
            icon: <Server size={24} />,
            url: '/', // Points to root/landing or potentially specific resource URL if available
            color: 'bg-blue-50 text-blue-600'
        }
    ];

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div>
                <h1 className="text-2xl font-bold text-slate-900">My Applications</h1>
                <p className="text-slate-500">Access authorized resources and tools</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {apps.map(app => (
                    <div key={app.id} className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow group">
                        <div className="flex items-start justify-between mb-4">
                            <div className={`p-3 rounded-lg ${app.color}`}>
                                {app.icon}
                            </div>
                            <a href={app.url} target="_blank" rel="noopener noreferrer" className="p-2 text-slate-400 hover:text-blue-600 transition-colors">
                                <ExternalLink size={18} />
                            </a>
                        </div>
                        <h3 className="font-bold text-slate-900 mb-1 group-hover:text-blue-600 transition-colors">{app.name}</h3>
                        <p className="text-sm text-slate-500 mb-4">{app.description}</p>
                        <a
                            href={app.url}
                            className="inline-flex items-center justify-center w-full px-4 py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 text-sm font-semibold rounded-lg transition-colors border border-slate-200"
                        >
                            Launch App
                        </a>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default UserApplications;
