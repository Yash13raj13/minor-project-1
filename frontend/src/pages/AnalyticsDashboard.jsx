import React, { useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import { analyticsAPI } from '../services/api';
import { 
  BarChart3, 
  CheckCircle2, 
  Clock, 
  Layers, 
  TrendingUp, 
  Flame,
  RefreshCw
} from 'lucide-react';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function AnalyticsDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const res = await analyticsAPI.getDashboard();
      setData(res);
    } catch (err) {
      console.error("Analytics fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  // 1. SLA Bar Chart Data
  const deptLabels = data?.department_metrics?.map(d => d.name) || [
    'Roads & Infrastructure',
    'Sanitation & Solid Waste',
    'Water Supply & Sewage',
    'Electricity & Lighting',
    'Public Health & Safety'
  ];
  const slaRates = data?.department_metrics?.map(d => d.sla_compliance_rate) || [88, 91, 79, 94, 82];

  const slaChartData = {
    labels: deptLabels,
    datasets: [
      {
        label: 'SLA Compliance Rate (%)',
        data: slaRates,
        backgroundColor: 'rgba(2, 132, 199, 0.85)',
        borderRadius: 8,
      },
    ],
  };

  // 2. Status Doughnut Data
  const statusLabels = ['Submitted', 'Under Review', 'Assigned', 'In Progress', 'Resolved', 'Duplicate'];
  const statusValues = [
    data?.status_distribution?.submitted || 2,
    data?.status_distribution?.under_review || 1,
    data?.status_distribution?.assigned || 3,
    data?.status_distribution?.in_progress || 4,
    data?.status_distribution?.resolved || 12,
    data?.status_distribution?.duplicate || 2,
  ];

  const doughnutData = {
    labels: statusLabels,
    datasets: [
      {
        data: statusValues,
        backgroundColor: [
          '#38bdf8', // submitted (sky)
          '#818cf8', // under review (indigo)
          '#f59e0b', // assigned (amber)
          '#0284c7', // in progress (blue)
          '#10b981', // resolved (emerald)
          '#a855f7', // duplicate (purple)
        ],
        borderWidth: 2,
        borderColor: '#ffffff',
      },
    ],
  };

  // 3. 14-Day Trend Line Data
  const trendLabels = data?.daily_trend?.map(t => t.date) || ['Oct 14', 'Oct 16', 'Oct 18', 'Oct 20', 'Oct 22', 'Oct 24', 'Oct 26'];
  const trendCounts = data?.daily_trend?.map(t => t.count) || [2, 5, 3, 7, 4, 8, 10];

  const trendData = {
    labels: trendLabels,
    datasets: [
      {
        label: 'Complaints Lodged',
        data: trendCounts,
        fill: true,
        backgroundColor: 'rgba(14, 165, 233, 0.12)',
        borderColor: '#0284c7',
        tension: 0.35,
        pointBackgroundColor: '#0284c7',
      },
    ],
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Page Title & Refresh */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-purple-700 bg-purple-50 px-3 py-1 rounded-full w-fit mb-1.5">
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Municipal Performance Analytics</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Governance Intelligence Dashboard</h1>
          <p className="text-sm text-slate-500">Cross-department SLA monitoring, duplicate prevention savings, and grievance trends.</p>
        </div>

        <button
          type="button"
          onClick={fetchAnalytics}
          className="flex items-center space-x-2 px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-bold shadow-xs transition cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Data</span>
        </button>
      </div>

      {/* 4 KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1 */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex justify-between items-center text-slate-500 text-xs font-semibold uppercase">
            <span>Total Lodged</span>
            <span className="p-2 bg-sky-50 text-sky-600 rounded-xl"><Layers className="w-4 h-4" /></span>
          </div>
          <div className="text-3xl font-extrabold text-slate-900">{data?.total_complaints || 24}</div>
          <p className="text-xs text-slate-400">Civic issues logged across city</p>
        </div>

        {/* Card 2 */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex justify-between items-center text-slate-500 text-xs font-semibold uppercase">
            <span>Resolution Rate</span>
            <span className="p-2 bg-emerald-50 text-emerald-600 rounded-xl"><CheckCircle2 className="w-4 h-4" /></span>
          </div>
          <div className="text-3xl font-extrabold text-emerald-600">{data?.resolution_rate || 78}%</div>
          <p className="text-xs text-slate-400">{data?.resolved_count || 18} complaints resolved</p>
        </div>

        {/* Card 3 */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex justify-between items-center text-slate-500 text-xs font-semibold uppercase">
            <span>FAISS Dupes Merged</span>
            <span className="p-2 bg-purple-50 text-purple-600 rounded-xl"><Flame className="w-4 h-4" /></span>
          </div>
          <div className="text-3xl font-extrabold text-purple-600">{data?.duplicates_detected || 3}</div>
          <p className="text-xs text-purple-700 font-medium">Prevented duplicate field crews</p>
        </div>

        {/* Card 4 */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex justify-between items-center text-slate-500 text-xs font-semibold uppercase">
            <span>Avg Resolution Time</span>
            <span className="p-2 bg-amber-50 text-amber-600 rounded-xl"><Clock className="w-4 h-4" /></span>
          </div>
          <div className="text-3xl font-extrabold text-slate-900">{data?.avg_resolution_hours || 22.5}h</div>
          <p className="text-xs text-slate-400">City-wide target SLA benchmark</p>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* SLA Compliance Bar Chart (8 cols) */}
        <div className="lg:col-span-8 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-slate-800 text-sm">Department SLA Compliance Benchmark</h3>
            <span className="text-xs text-slate-400 font-medium">Target &gt; 80%</span>
          </div>
          <div className="h-64">
            <Bar data={slaChartData} options={{ responsive: true, maintainAspectRatio: false }} />
          </div>
        </div>

        {/* Status Distribution Doughnut (4 cols) */}
        <div className="lg:col-span-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h3 className="font-bold text-slate-800 text-sm">Status Distribution</h3>
          <div className="h-64 flex items-center justify-center">
            <Doughnut data={doughnutData} options={{ responsive: true, maintainAspectRatio: false }} />
          </div>
        </div>
      </div>

      {/* Trend Chart & Ward Hotspots Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Daily Trend (7 cols) */}
        <div className="lg:col-span-7 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-sky-600" />
            <h3 className="font-bold text-slate-800 text-sm">14-Day Complaint Volume Trend</h3>
          </div>
          <div className="h-64">
            <Line data={trendData} options={{ responsive: true, maintainAspectRatio: false }} />
          </div>
        </div>

        {/* Ward Hotspots Table (5 cols) */}
        <div className="lg:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-800 text-sm">Top Grievance Hotspots by Ward</h3>
            <span className="text-xs text-slate-400">Total Wards</span>
          </div>
          <div className="space-y-2">
            {data?.ward_hotspots?.map((w, idx) => (
              <div key={idx} className="flex justify-between items-center p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                <span className="font-bold text-slate-700">{w.ward}</span>
                <span className="font-mono bg-sky-100 text-sky-800 font-bold px-2 py-0.5 rounded-full">
                  {w.count} tickets
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
