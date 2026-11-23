import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import CitizenPortal from './pages/CitizenPortal';
import OfficerDashboard from './pages/OfficerDashboard';
import AdminDashboard from './pages/AdminDashboard';
import GrievanceMap from './pages/GrievanceMap';
import AnalyticsDashboard from './pages/AnalyticsDashboard';
import LoginPage from './pages/LoginPage';

function AppContent() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('citizen');

  const handleLoginSuccess = (role) => {
    if (role === 'ADMIN') setActiveTab('admin');
    else if (role === 'OFFICER') setActiveTab('officer');
    else setActiveTab('citizen');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="flex-1">
        {activeTab === 'login' && <LoginPage onLoginSuccess={handleLoginSuccess} />}
        {activeTab === 'citizen' && <CitizenPortal />}
        {activeTab === 'officer' && <OfficerDashboard />}
        {activeTab === 'admin' && <AdminDashboard />}
        {activeTab === 'map' && <GrievanceMap />}
        {activeTab === 'analytics' && <AnalyticsDashboard />}
      </main>
      <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
        <p className="font-medium text-slate-700">CivicLens — AI-Powered Governance Complaint Intelligence Platform</p>
        <p className="mt-1 text-slate-400">FastAPI • PostgreSQL • Hugging Face • FAISS • React.js • Leaflet • Chart.js</p>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
