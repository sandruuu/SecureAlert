import React, { useState } from 'react';
import axios from 'axios';
import { Smartphone, Check, Lock, ChevronRight } from 'lucide-react';

const SetupAuthenticator = () => {
    const [step, setStep] = useState('start'); // start, show_qr, verify
    const [setupData, setSetupData] = useState(null);
    const [code, setCode] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);

    const startSetup = async () => {
        try {
            const resp = await axios.post('/api/user/mfa/setup');
            setSetupData(resp.data);
            setStep('show_qr');
            setError('');
        } catch (err) {
            setError('Failed to enhance security. Please try again.');
        }
    };

    const verifySetup = async () => {
        try {
            await axios.post('/api/user/mfa/activate', {
                secret: setupData.secret,
                code: code
            });
            setSuccess(true);
            setStep('complete');
        } catch (err) {
            setError('Invalid code. Please try again.');
        }
    };

    if (success) {
        return (
            <div className="bg-green-50 border border-green-200 rounded-2xl p-6 flex items-center gap-4">
                <div className="bg-green-100 p-3 rounded-full text-green-600">
                    <Check size={24} />
                </div>
                <div>
                    <h3 className="font-bold text-green-800">Authenticator Active</h3>
                    <p className="text-sm text-green-600">Your account is now protected with 2FA.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm overflow-hidden">
            <div className="flex items-start gap-4 mb-6">
                <div className="bg-blue-50 p-3 rounded-xl text-blue-600">
                    <Smartphone size={24} />
                </div>
                <div>
                    <h3 className="font-bold text-slate-900">Authenticator App</h3>
                    <p className="text-sm text-slate-500">Secure your account with Google Authenticator or similar apps.</p>
                </div>
            </div>

            {step === 'start' && (
                <button
                    onClick={startSetup}
                    className="w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100 rounded-xl transition-colors group"
                >
                    <span className="font-semibold text-slate-700">Setup 2FA</span>
                    <ChevronRight size={20} className="text-slate-400 group-hover:text-slate-900" />
                </button>
            )}

            {step === 'show_qr' && setupData && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
                    <div className="flex justify-center bg-white p-4 rounded-xl border border-slate-100">
                        <img src={setupData.qr_code} alt="2FA QR Code" className="w-48 h-48 mix-blend-multiply" />
                    </div>

                    <div className="space-y-2">
                        <p className="text-sm font-medium text-slate-700 text-center">Scan this code with your Authenticator App</p>
                        <p className="text-xs text-slate-400 text-center font-mono select-all bg-slate-50 p-1 rounded">{setupData.secret}</p>
                    </div>

                    <div className="space-y-3">
                        <input
                            type="text"
                            placeholder="Enter 6-digit code"
                            value={code}
                            onChange={(e) => setCode(e.target.value)}
                            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-3 text-center font-mono text-lg tracking-widest outline-none focus:border-blue-500 transition-colors"
                            maxLength={6}
                        />
                        <button
                            onClick={verifySetup}
                            disabled={code.length !== 6}
                            className="w-full bg-slate-900 text-white font-bold py-3 rounded-xl hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                        >
                            Activate
                        </button>
                    </div>

                    {error && <p className="text-center text-xs text-red-500 font-bold">{error}</p>}
                </div>
            )}
        </div>
    );
};

export default SetupAuthenticator;
