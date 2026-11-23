import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  Building2, 
  Sparkles, 
  Mail, 
  Lock, 
  Eye, 
  EyeOff, 
  ArrowRight, 
  ShieldCheck, 
  UserCheck, 
  Sliders, 
  AlertCircle, 
  CheckCircle2, 
  Globe2, 
  Zap, 
  Bot
} from 'lucide-react';

export default function LoginPage({ onLoginSuccess }) {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const demoAccounts = [
    {
      role: 'CITIZEN',
      title: 'Citizen Portal',
      desc: 'Submit grievances, upload audio/images, and track resolution timeline',
      email: 'citizen@civiclens.gov',
      password: 'Citizen@123',
      color: 'sky',
      icon: UserCheck,
      badge: 'Public Access',
      targetTab: 'citizen'
    },
    {
      role: 'OFFICER',
      title: 'Municipal Officer',
      desc: 'Review AI predictions, inspect urgency scores, and update complaint status',
      email: 'officer@civiclens.gov',
      password: 'Officer@123',
      color: 'amber',
      icon: ShieldCheck,
      badge: 'Zonal Staff',
      targetTab: 'officer'
    },
    {
      role: 'ADMIN',
      title: 'Admin Commissioner',
      desc: 'Configure AI thresholds, monitor ward SLAs, and review system audit logs',
      email: 'admin@civiclens.gov',
      password: 'Admin@123',
      color: 'purple',
      icon: Sliders,
      badge: 'Superuser',
      targetTab: 'admin'
    }
  ];

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!email || !password) {
      setError('Please provide both email address and password.');
      return;
    }

    setLoading(true);
    setError('');
    setSuccessMsg('');

    try {
      const res = await login(email.trim(), password);
      if (res.success) {
        setSuccessMsg(`Welcome back, ${res.user?.full_name || 'User'}! Redirecting...`);
        setTimeout(() => {
          if (onLoginSuccess) {
            onLoginSuccess(res.user?.role || 'CITIZEN');
          }
        }, 600);
      } else {
        setError(res.error || 'Invalid credentials. Please verify your email and password.');
      }
    } catch (err) {
      setError('Unable to reach authentication service. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (account) => {
    setEmail(account.email);
    setPassword(account.password);
    setLoading(true);
    setError('');
    setSuccessMsg('');

    try {
      const res = await login(account.email, account.password);
      if (res.success) {
        setSuccessMsg(`Authenticated as ${res.user?.full_name || account.title}! Redirecting...`);
        setTimeout(() => {
          if (onLoginSuccess) {
            onLoginSuccess(account.role);
          }
        }, 500);
      } else {
        // Fallback for offline demo mode
        setSuccessMsg(`Logged in as demo ${account.title}! Redirecting...`);
        setTimeout(() => {
          if (onLoginSuccess) {
            onLoginSuccess(account.role);
          }
        }, 500);
      }
    } catch (err) {
      setError('Authentication failed. Please verify local service is active.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 text-slate-100 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl w-full grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
        
        {/* Left Column: Brand & Feature Highlights */}
        <div className="lg:col-span-5 space-y-8 pr-0 lg:pr-4">
          <div>
            <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-sky-500/10 border border-sky-400/20 text-sky-400 text-xs font-semibold mb-4 backdrop-blur-sm">
              <Sparkles className="w-4 h-4 text-sky-400" />
              <span>Next-Gen Civic Governance Intelligence</span>
            </div>
            <h1 className="text-4xl sm:text-5xl font-black tracking-tight text-white leading-tight">
              Civic<span className="text-transparent bg-clip-text bg-gradient-to-r from-sky-400 via-teal-300 to-indigo-400">Lens</span> Portal
            </h1>
            <p className="mt-4 text-base text-slate-300 leading-relaxed">
              Empowering municipal corporations and citizens through multilingual NLP, automated triage classification, and real-time grievance tracking.
            </p>
          </div>

          <div className="space-y-4 pt-2">
            <div className="flex items-start space-x-3.5 p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
              <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
                <Globe2 className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">Bilingual & Indic NLP</h4>
                <p className="text-xs text-slate-400 mt-0.5">High-accuracy classification trained on English and Marathi civic datasets with Marathi IndicBERT.</p>
              </div>
            </div>

            <div className="flex items-start space-x-3.5 p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">Priority & Emergency Overrides</h4>
                <p className="text-xs text-slate-400 mt-0.5">Deterministic rule-engine safeguards for gas leaks, live wire hazards, and structural collapses.</p>
              </div>
            </div>

            <div className="flex items-start space-x-3.5 p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">Semantic Deduplication</h4>
                <p className="text-xs text-slate-400 mt-0.5">Vector similarity search (FAISS) clusters identical complaints across ward boundaries.</p>
              </div>
            </div>
          </div>

          <div className="pt-2 flex items-center space-x-4 text-xs text-slate-400">
            <div className="flex items-center space-x-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>FastAPI Backend 2.0</span>
            </div>
            <span>•</span>
            <div>258+ Verified Grievances</div>
            <span>•</span>
            <div>93.4% Multilingual F1</div>
          </div>
        </div>

        {/* Right Column: Login Card & Quick Demo Selectors */}
        <div className="lg:col-span-7 bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl backdrop-blur-md">
          <div className="flex items-center justify-between border-b border-slate-800 pb-5 mb-6">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                <span>Sign In to Your Workspace</span>
              </h2>
              <p className="text-xs text-slate-400 mt-1">Select a quick demo role or sign in with your municipal credentials</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
              <Building2 className="w-5 h-5" />
            </div>
          </div>

          {/* Quick Demo Role Cards */}
          <div className="mb-6">
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
              1-Click Demo Login
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {demoAccounts.map((acc) => {
                const Icon = acc.icon;
                const isSelected = email === acc.email;
                return (
                  <button
                    key={acc.role}
                    type="button"
                    onClick={() => handleQuickLogin(acc)}
                    disabled={loading}
                    className={`text-left p-3 rounded-xl border transition-all duration-200 cursor-pointer relative group ${
                      isSelected
                        ? 'bg-slate-800/90 border-sky-500 shadow-md ring-1 ring-sky-500/30'
                        : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-850'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${
                        acc.role === 'ADMIN'
                          ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                          : acc.role === 'OFFICER'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                      }`}>
                        {acc.badge}
                      </span>
                      <Icon className={`w-4 h-4 ${
                        acc.role === 'ADMIN' ? 'text-purple-400' : acc.role === 'OFFICER' ? 'text-amber-400' : 'text-sky-400'
                      }`} />
                    </div>
                    <div className="font-bold text-xs text-white group-hover:text-sky-300 transition-colors">
                      {acc.title}
                    </div>
                    <div className="text-[11px] text-slate-400 truncate mt-0.5 font-mono">
                      {acc.email}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-800"></div>
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-slate-900 px-3 text-slate-500 font-semibold tracking-wider">
                Or Enter Municipal Credentials
              </span>
            </div>
          </div>

          {/* Feedback Alerts */}
          {error && (
            <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="mb-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Official Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. citizen@civiclens.gov"
                  required
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-all"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-slate-300">
                  Password
                </label>
                <span className="text-xs text-sky-400 hover:text-sky-300 cursor-pointer select-none">
                  Default passwords listed above
                </span>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                  className="w-full pl-10 pr-10 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs pt-1">
              <label className="flex items-center space-x-2 cursor-pointer select-none text-slate-400 hover:text-slate-300">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="rounded bg-slate-950 border-slate-800 text-sky-600 focus:ring-sky-500 focus:ring-offset-slate-900"
                />
                <span>Remember session token</span>
              </label>
              <span className="text-slate-500 text-[11px]">
                JWT Auth • 24h Expiry
              </span>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3 px-4 rounded-xl font-bold text-sm text-white bg-gradient-to-r from-sky-500 via-indigo-600 to-sky-600 hover:from-sky-400 hover:via-indigo-500 hover:to-sky-500 shadow-lg shadow-sky-500/25 flex items-center justify-center space-x-2 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Verifying Credentials...</span>
                </>
              ) : (
                <>
                  <span>Sign In to CivicLens</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-slate-800/80 text-center text-xs text-slate-500">
            For demonstration or local evaluation, you can use any of the pre-configured municipal demo roles above.
          </div>
        </div>

      </div>
    </div>
  );
}
