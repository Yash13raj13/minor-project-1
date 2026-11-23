import React from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  Building2, 
  FileText, 
  ShieldCheck, 
  MapPin, 
  BarChart3, 
  Sparkles,
  UserCheck, 
  Sliders,
  LogIn,
  LogOut
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab }) {
  const { user, logout, switchDemoRole } = useAuth();

  const navItems = [
    { id: 'citizen', label: 'Citizen Portal', icon: FileText },
    { id: 'officer', label: 'Officer Triaging', icon: ShieldCheck },
    { id: 'admin', label: 'Admin Console', icon: Sliders },
    { id: 'map', label: 'Grievance Map', icon: MapPin },
    { id: 'analytics', label: 'Governance Analytics', icon: BarChart3 },
  ];

  const handleRoleSwitch = async (role) => {
    await switchDemoRole(role);
    if (role === 'CITIZEN') setActiveTab('citizen');
    else if (role === 'OFFICER') setActiveTab('officer');
    else if (role === 'ADMIN') setActiveTab('admin');
  };

  const handleLogout = () => {
    logout();
    setActiveTab('login');
  };

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

          {/* Role Switcher Pill & Auth Controls */}
          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center bg-slate-800 border border-slate-700 rounded-xl p-1 shadow-inner">
              <span className="text-xs text-slate-400 px-2 items-center flex">
                <UserCheck className="w-3.5 h-3.5 mr-1 text-slate-300" /> Role:
              </span>
              <button
                type="button"
                onClick={() => handleRoleSwitch('CITIZEN')}
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
                onClick={() => handleRoleSwitch('OFFICER')}
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
                onClick={() => handleRoleSwitch('ADMIN')}
                className={`text-xs px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                  user?.role === 'ADMIN' 
                    ? 'bg-purple-600 text-white shadow-sm ring-1 ring-purple-400' 
                    : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                Admin
              </button>
            </div>

            {/* Login / User Session Profile Button */}
            {user ? (
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => setActiveTab('login')}
                  title="Switch User / Login Page"
                  className={`flex items-center space-x-2 px-2.5 py-1.5 rounded-xl border transition-all cursor-pointer ${
                    activeTab === 'login'
                      ? 'bg-sky-600/30 border-sky-400 text-sky-200'
                      : 'bg-slate-800/80 border-slate-700 hover:border-slate-600 text-slate-300 hover:text-white'
                  }`}
                >
                  <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center font-bold text-white text-xs">
                    {user?.full_name ? user.full_name.charAt(0) : 'U'}
                  </div>
                  <span className="text-xs font-medium hidden lg:inline max-w-[120px] truncate">
                    {user.full_name?.split(' ')[0]}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={handleLogout}
                  title="Sign Out"
                  className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-xl transition-all cursor-pointer"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setActiveTab('login')}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  activeTab === 'login'
                    ? 'bg-sky-600 text-white shadow-sm ring-1 ring-sky-400'
                    : 'bg-sky-500/10 text-sky-400 hover:bg-sky-500/20 border border-sky-500/30'
                }`}
              >
                <LogIn className="w-4 h-4" />
                <span>Sign In</span>
              </button>
            )}

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
        <button
          type="button"
          onClick={() => setActiveTab('login')}
          className={`flex-1 flex items-center justify-center space-x-1.5 py-2 px-2 rounded-md text-xs font-semibold whitespace-nowrap cursor-pointer ${
            activeTab === 'login' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:bg-slate-800'
          }`}
        >
          <LogIn className="w-3.5 h-3.5" />
          <span>Login</span>
        </button>
      </div>
    </header>
  );
}
