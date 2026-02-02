import { useState, useEffect } from 'react'
import { startRegistration, startAuthentication } from '@simplewebauthn/browser'
import axios from 'axios'
import { User, ChevronRight, Fingerprint, RefreshCw, AlertCircle, ShieldAlert, ShieldCheck, Loader2, Copy } from 'lucide-react'

const LoginPage = ({ onLoginSuccess, initialStep = 'login', initialToken = '', initialScore = 0, logoutReason = '' }) => {
    // Steps: 'login', 'posture', 'mfa'
    const [verificationStep, setVerificationStep] = useState(initialStep)

    const [username, setUsername] = useState('')
    const [inviteCode, setInviteCode] = useState('')
    const [error, setError] = useState(logoutReason)
    const [loading, setLoading] = useState(false)
    const [isRegistering, setIsRegistering] = useState(false)
    const [mounted, setMounted] = useState(false)

    // Posture State
    const [enrollmentToken, setEnrollmentToken] = useState(initialToken)
    const [trustScore, setTrustScore] = useState(initialScore)

    // MFA State
    const [showMFA, setShowMFA] = useState(false)
    const [tempToken, setTempToken] = useState('')
    const [mfaType, setMfaType] = useState('email')
    const [otpCode, setOtpCode] = useState('')

    // Animation trigger
    useState(() => {
        setTimeout(() => setMounted(true), 100)
    }, [])

    // Polling for Posture Check
    useEffect(() => {
        let interval;
        if (verificationStep === 'posture') {
            interval = setInterval(async () => {
                try {
                    // CORRECTED URL: /api/session/status (maps to backend /session/status)
                    const res = await axios.get('/api/session/status');
                    setTrustScore(res.data.score || 0);

                    if (res.data.status === 'active') {
                        clearInterval(interval);
                        setLoading(false);
                        onLoginSuccess(res.data);
                    } else if (res.data.status === 'mfa_required') {
                        // If we improved from Low to Medium, backend might require MFA.
                        // This path would require handling MFA triggers from polling.
                        // For now, assuming direct jump to Active (Score >= 75)
                        clearInterval(interval);
                        setVerificationStep('mfa');
                        setShowMFA(true);
                    }
                } catch (e) {
                    // Ignore errors during polling (e.g. 403 pending)
                }
            }, 3000);
        }
        return () => clearInterval(interval);
    }, [verificationStep, onLoginSuccess]);

    // Trigger MFA Challenge if entering MFA step without tempToken (e.g. from transition)
    useEffect(() => {
        if (verificationStep === 'mfa' && !tempToken) {
            const requestChallenge = async () => {
                try {
                    setLoading(true);
                    const res = await axios.post('/api/auth/mfa/challenge');
                    if (res.data.temp_token) {
                        setTempToken(res.data.temp_token);
                        setMfaType(res.data.mfa_type);
                    }
                } catch (e) {
                    setError("Failed to initiate MFA. Please try again.");
                } finally {
                    setLoading(false);
                }
            };
            requestChallenge();
        }
    }, [verificationStep, tempToken]);

    // Sync state with props when they change (e.g. forced logout while on login page)
    useEffect(() => {
        setVerificationStep(initialStep)
    }, [initialStep])

    useEffect(() => {
        if (logoutReason) setError(logoutReason)
    }, [logoutReason])

    const handleRegister = async (e) => {
        if (e) e.preventDefault();
        if (!username || !inviteCode) return setError('Email and Invite Code required')
        setLoading(true)
        setError('')
        try {
            const resp = await axios.post('/api/register/options', { username, invite_code: inviteCode })
            const attResp = await startRegistration(resp.data)
            const verResp = await axios.post('/api/register/verify', { username, invite_code: inviteCode, response: attResp })
            if (verResp.data.verified) {
                alert('Device Verification Successful! You will be redirected.')
                setIsRegistering(false)
                setInviteCode('')
                handleLoginFIDO()
            }
        } catch (err) {
            console.error(err)
            setError(err.response?.data?.detail || err.message)
            setLoading(false)
        }
    }

    // Login Handler
    const handleLoginFIDO = async (e) => {
        if (e) e.preventDefault();
        if (!username) return setError('Please enter your email')
        setLoading(true)
        setError('')
        try {
            const resp = await axios.post('/api/login/options', { username })

            // Check if resp.data wraps the options in a specific property like 'options' or 'publicKey'
            // SimpleWebAuthn browser expects JSON with Public Key options.
            const asseResp = await startAuthentication(resp.data)
            const verResp = await axios.post('/api/login/verify', { username, response: asseResp })

            const data = verResp.data;

            // CASE 1: Posture Check Required
            if (data.status === 'posture_required') {
                setEnrollmentToken(data.enrollment_token || '');
                setTrustScore(data.score || 0);
                setVerificationStep('posture');
                setLoading(true); // Keep loading state visually or handle differently
                return;
            }

            // CASE 2: MFA Required
            if (data.mfa_required || data.status === 'mfa_required') {
                setLoading(false);
                setTempToken(data.temp_token)
                setMfaType(data.mfa_type)
                setShowMFA(true)
                setVerificationStep('mfa');
                return;
            }

            // CASE 3: Active
            if (data.verified && data.status === 'active') {
                onLoginSuccess(data)
            }
        } catch (err) {
            console.error(err)
            setError(err.response?.data?.detail || err.message || 'Authentication Failed')
            setLoading(false)
        }
    }

    // MFA Handler
    const handleVerifyMFA = async (e) => {
        if (e) e.preventDefault();
        setLoading(true)
        setError('')
        try {
            const resp = await axios.post('/api/auth/mfa/verify', { temp_token: tempToken, code: otpCode })
            if (resp.data.verified) {
                onLoginSuccess(resp.data)
            }
        } catch (err) {
            setError(err.response?.data?.detail || 'Invalid Code')
            setLoading(false)
        }
    }

    const copyToken = () => {
        navigator.clipboard.writeText(enrollmentToken);
        alert("Token copied!");
    }

    return (
        <div className="min-h-screen w-full flex items-center justify-center bg-slate-50 font-sans p-4 relative overflow-hidden">
            {/* Background Decorative Elements */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-[#FF5F1F]/5 rounded-full blur-[120px] -translate-y-1/2"></div>
                <div className="absolute bottom-0 right-0 w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-[100px] translate-y-1/2 translate-x-1/3"></div>
            </div>

            <div className={`w-full max-w-[440px] bg-white border border-slate-200 shadow-2xl shadow-slate-200/50 rounded-2xl p-8 md:p-12 z-10 relative transition-all duration-700 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>

                {/* --- LOGO SECTION --- */}
                <div className="flex flex-col items-center justify-center mb-10">
                    <div className="w-16 h-20 relative mb-2">
                        <svg className="w-full h-full drop-shadow-md" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 22C12 22 20 18 20 12V5L12 2L4 5V12C4 18 12 22 12 22Z" className="fill-slate-900 stroke-slate-700" strokeWidth="1" />
                            <circle cx="12" cy="14" r="2.5" className="fill-white" />
                            <path d="M12 16.5V18.5" className="stroke-white" strokeWidth="2" strokeLinecap="round" />
                            <path d="M8.5 8C9.5 7 10.5 6.5 12 6.5C13.5 6.5 14.5 7 15.5 8" className="stroke-white/80" strokeWidth="1.5" strokeLinecap="round" />
                            <path d="M7 6.5C8.5 5 10 4.5 12 4.5C14 4.5 15.5 5 17 6.5" className="stroke-white/50" strokeWidth="1.5" strokeLinecap="round" />
                            <path d="M10 9.5C10.5 9 11.25 8.7 12 8.7C12.75 8.7 13.5 9 14 9.5" className="stroke-white" strokeWidth="1.5" strokeLinecap="round" />
                        </svg>
                    </div>
                    <h2 className="text-xl font-bold tracking-widest text-slate-900">
                        SECURE<span className="text-[#FF5F1F]">LOGIN</span>
                    </h2>
                    <p className="text-xs text-slate-400 font-medium tracking-wide uppercase mt-1">
                        {verificationStep === 'posture' ? "Security Check Required" : (isRegistering ? "Activate New Account" : "Passwordless Access")}
                    </p>
                </div>

                {/* --- POSTURE CHECK UI --- */}
                {verificationStep === 'posture' ? (
                    <div className="space-y-6 animate-in fade-in slide-in-from-right-8">
                        <div className="rounded-xl p-5 text-center space-y-3">
                            <div className="mx-auto w-12 h-12 rounded-full flex items-center justify-center relative">
                                <Loader2 className="text-orange-600 animate-spin" size={24} />
                            </div>
                            <div>
                                <h3 className="text-sm font-bold text-slate-900">Waiting for Device Agent...</h3>
                            </div>
                        </div>

                        {enrollmentToken && (
                            <div className="space-y-2">
                                <div className="flex justify-between items-center px-1">
                                    <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">Enrollment Token</label>
                                    <span className="text-xs text-orange-600 font-medium">Agent Required</span>
                                </div>
                                <div className="relative group cursor-pointer" onClick={copyToken}>
                                    <div className="w-full bg-slate-900 rounded-xl py-3 px-4 font-mono text-sm text-white break-all pr-10 hover:bg-slate-800 transition-colors">
                                        {enrollmentToken}
                                    </div>
                                    <div className="absolute right-3 top-3 text-slate-400">
                                        <Copy size={16} />
                                    </div>
                                </div>
                            </div>
                        )}

                        {!enrollmentToken && (
                            <div className="text-center text-xs text-slate-500">
                                Please ensure your <strong>SecureAlert Agent</strong> is running and that your Firewall/Antivirus are enabled.
                            </div>
                        )}

                        <button
                            onClick={() => window.location.reload()}
                            className="w-full py-3 text-sm font-bold text-slate-400 hover:text-slate-600 transition-colors"
                        >
                            Cancel
                        </button>
                    </div>
                ) : (
                    /* --- NORMAL LOGIN / MFA FORM --- */
                    <form onSubmit={isRegistering ? handleRegister : (showMFA ? handleVerifyMFA : handleLoginFIDO)} className="space-y-6">
                        {!showMFA ? (
                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-slate-700 uppercase tracking-wide ml-1">Email Address</label>
                                <div className="relative group">
                                    <div className="absolute left-4 top-3.5 text-slate-400 group-focus-within:text-slate-900 transition-colors">
                                        <User size={18} />
                                    </div>
                                    <input
                                        type="text"
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        className="w-full bg-white border border-slate-200 hover:border-slate-900 rounded-xl py-3 pl-11 pr-4 text-sm font-medium text-slate-900 focus:border-slate-900 focus:ring-4 focus:ring-slate-900/10 transition-all outline-none placeholder:text-slate-400 shadow-sm"
                                        placeholder="Enter your email"
                                    />
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-4 animate-in fade-in slide-in-from-right-4">
                                <div className="border border-blue-100 rounded-xl p-4 flex items-start gap-3">
                                    <AlertCircle className="text-blue-600 shrink-0 mt-0.5" size={18} />
                                    <div>
                                        <p className="text-sm font-bold text-blue-800">Additional Verification Required</p>
                                        <p className="text-xs text-blue-600 mt-1">
                                            {mfaType === 'totp'
                                                ? "Please enter the code from your Authenticator App."
                                                : "We detected a new device. Please enter the code sent to your email."}
                                        </p>
                                    </div>
                                </div>

                                <div className="space-y-1.5">
                                    <label className="text-xs font-bold text-slate-700 uppercase tracking-wide ml-1">Verification Code</label>
                                    <input
                                        type="text"
                                        value={otpCode}
                                        onChange={(e) => setOtpCode(e.target.value)}
                                        className="w-full bg-slate-50 border border-slate-200 rounded-xl py-3 px-4 text-center text-2xl font-mono tracking-[0.5em] text-slate-900 focus:border-blue-500 outline-none"
                                        placeholder="000000"
                                        maxLength={6}
                                        autoFocus
                                    />
                                </div>
                            </div>
                        )}

                        {isRegistering && (
                            <div className="space-y-1.5 animate-in slide-in-from-top-2 fade-in">
                                <label className="text-xs font-bold text-slate-700 uppercase tracking-wide ml-1">Invitation Code</label>
                                <div className="relative group">
                                    <input
                                        type="text"
                                        value={inviteCode}
                                        onChange={(e) => setInviteCode(e.target.value)}
                                        className="w-full bg-white border border-slate-200 hover:border-slate-900 rounded-xl py-3 px-4 text-sm font-medium text-slate-900 focus:border-slate-900 focus:ring-4 focus:ring-slate-900/10 transition-all outline-none placeholder:text-slate-400 shadow-sm font-mono tracking-widest text-center uppercase"
                                        placeholder="CODE"
                                    />
                                </div>
                                <p className="text-[10px] text-slate-400 ml-1">Check your email for the code.</p>
                            </div>
                        )}

                        <div className="pt-2">
                            {error && (
                                <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-100 text-red-600 flex items-start gap-2 animate-in text-sm font-semibold">
                                    <AlertCircle className="shrink-0 mt-0.5" size={16} />
                                    <span>{error}</span>
                                </div>
                            )}

                            <button
                                type="submit"
                                disabled={loading && verificationStep !== 'posture'}
                                className={`w-full font-bold py-3.5 rounded-xl transition-all shadow-lg active:scale-[0.98] disabled:opacity-70 disabled:pointer-events-none flex items-center justify-center gap-2 ${isRegistering ? 'bg-slate-900 hover:bg-slate-800 text-white shadow-slate-900/20' : 'bg-[#FF5F1F] hover:bg-[#E04F16] text-white shadow-[#FF5F1F]/20'}`}
                            >
                                {loading && verificationStep !== 'posture' ? (
                                    <>
                                        <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        <span>Processing...</span>
                                    </>
                                ) : (
                                    <>
                                        {isRegistering ? (
                                            <>
                                                <RefreshCw size={18} />
                                                <span>Activate</span>
                                            </>
                                        ) : (
                                            <>
                                                {showMFA ? (
                                                    <span>Verify Code</span>
                                                ) : (
                                                    <>
                                                        <Fingerprint size={20} />
                                                        <span>Authenticate</span>
                                                    </>
                                                )}
                                            </>
                                        )}
                                    </>
                                )}
                            </button>
                        </div>
                    </form>
                )}

                <div className="relative my-8">
                    <div className="absolute inset-0 flex items-center">
                    </div>
                </div>

                <div className="text-center">
                    {isRegistering ? (
                        <div className="space-y-2 animate-in fade-in">
                            <p className="text-sm text-slate-500">Already have an active device?</p>
                            <button onClick={() => { setIsRegistering(false); setError(''); }} className="text-sm font-bold text-slate-900 hover:underline">
                                Back to Login
                            </button>
                        </div>
                    ) : (
                        verificationStep !== 'posture' && !showMFA && (
                            <div className="space-y-2 animate-in fade-in">
                                <p className="text-sm text-slate-500">First time here?</p>
                                <button onClick={() => { setIsRegistering(true); setError(''); }} className="text-sm font-bold text-[#FF5F1F] hover:underline">
                                    Activate New Account
                                </button>
                            </div>
                        )
                    )}
                </div>

                <div className="mt-8 pt-6 border-t border-slate-50 flex justify-center">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-slate-300">
                        &copy; 2026 SecureAlert Systems
                    </span>
                </div>
            </div>
        </div>
    )
}

export default LoginPage
