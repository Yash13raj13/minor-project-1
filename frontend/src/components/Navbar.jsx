import React from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  Building2, 
  FileText, 
  ShieldCheck, 
  MapPin, 
  BarChart3, 
  Sparkles,
  UserCheck
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab }) {
  const { user, switchDemoRole } = useAuth();

  const navItems = [
    { id: 'citizen', label: 'Citizen Portal', icon: FileText },
    { id: 'officer', label: 'Officer Triaging', icon: ShieldCheck },
    { id: 'map', label: 'Grievance Map', icon: MapPin },
    { id: 'analytics', label: 'Governance Analytics', icon: BarChart3 },
  ];

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-50 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div 
            className="flex items-center space-x-3 cursor-pointer select-none" 
            onClick={() => setActiveTab('citizen')}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <Building2 className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-xl tracking-tight text-white">CivicLens</span>
                <span className="bg-sky-500/20 text-sky-400 border border-sky-500/30 text-[10px] font-semibold px-2 py-0.5 rounded-full flex items-center">
                  <Sparkles className="w-3 h-3 mr-1" /> AI Powered
                </span>
              </div>
              <p className="text-xs text-slate-400">Grievance Intelligence & Analytics</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-sm font-semibold transition-all cursor-pointer ${
                    isActive
                      ? 'bg-sky-600 text-white shadow-sm ring-1 ring-sky-400'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Role Switcher Pill */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center bg-slate-800 border border-slate-700 rounded-xl p-1 shadow-inner">
              <span className="hidden sm:flex text-xs text-slate-400 px-2 items-center">
                <UserCheck className="w-3.5 h-3.5 mr-1 text-slate-300" /> Role:
              </span>
              <button
                type="button"
                onClick={() => switchDemoRole('CITIZEN')}
                className={`text-xs px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                  user?.role === 'CITIZEN' 
                    ? 'bg-sky-600 text-white shadow-sm ring-1 ring-sky-400' 
                    : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                Citizen
              </button>
              <button
                type="button"
                onClick={() => switchDemoRole('OFFICER')}
                className={`text-xs px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                  user?.role === 'OFFICER' 
                    ? 'bg-amber-600 text-white shadow-sm ring-1 ring-amber-400' 
                    : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                Officer
              </button>
              <button
                type="button"
                onClick={() => switchDemoRole('ADMIN')}
                className={`text-xs px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                  user?.role === 'ADMIN' 
                    ? 'bg-purple-600 text-white shadow-sm ring-1 ring-purple-400' 
                    : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                Admin
              </button>
            </div>

            <div className="hidden lg:flex items-center space-x-2 text-right">
              <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center font-bold text-sky-400 text-xs border border-slate-600">
                {user?.full_name?.charAt(0) || 'U'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Tab Bar */}
      <div className="md:hidden flex overflow-x-auto border-t border-slate-800 px-2 py-1.5 space-x-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              type="button"
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex-1 flex items-center justify-center space-x-1.5 py-2 px-2 rounded-md text-xs font-semibold whitespace-nowrap cursor-pointer ${
                isActive ? 'bg-sky-600 text-white' : 'text-slate-400 hover:bg-slate-800'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </header>
  );
}
