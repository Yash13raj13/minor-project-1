import React, { useState, useEffect } from 'react';
import { 
  PlusCircle, 
  Search, 
  Filter, 
  MapPin, 
  Calendar, 
  Sparkles, 
  Layers,
  AlertCircle,
  RefreshCw
} from 'lucide-react';
import { complaintAPI } from '../services/api';
import { StatusBadge, PriorityBadge } from '../components/Badges';
import FileComplaintModal from '../components/FileComplaintModal';

export default function CitizenPortal() {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const fetchComplaints = async () => {
    try {
      setLoading(true);
      const params = {};
      if (statusFilter) params.status = statusFilter;
      if (search) params.search = search;
      const data = await complaintAPI.list(params);
      setComplaints(data || []);
    } catch (err) {
      console.error("Failed to fetch complaints:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComplaints();
  }, [statusFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchComplaints();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Banner / Header */}
      <div className="bg-gradient-to-r from-sky-600 via-sky-700 to-indigo-800 rounded-3xl p-6 sm:p-8 text-white shadow-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md text-xs font-medium text-sky-100">
            <Sparkles className="w-3.5 h-3.5 text-sky-300" />
            <span>AI Governance Portal</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Citizen Grievance Redressal</h1>
          <p className="text-sky-100 text-sm max-w-xl">
            Report local municipal issues in seconds. CivicLens uses AI to identify departments, detect duplicate tickets, and alert authorities immediately.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="shrink-0 flex items-center space-x-2 px-6 py-3.5 rounded-2xl bg-white text-sky-700 hover:bg-sky-50 font-bold text-sm shadow-lg transition-transform active:scale-95 cursor-pointer"
        >
          <PlusCircle className="w-5 h-5 text-sky-600" />
          <span>File New Grievance</span>
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-3 items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-96 flex gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              placeholder="Search by tracking number, title, or keyword..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
          </div>
          <button
            type="submit"
            className="px-4 py-2.5 bg-sky-600 hover:bg-sky-700 text-white rounded-xl text-xs font-bold transition cursor-pointer"
          >
            Search
          </button>
        </form>

        <div className="flex items-center space-x-3 w-full md:w-auto justify-end">
          <button
            type="button"
            onClick={fetchComplaints}
            className="p-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 transition"
            title="Refresh List"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 cursor-pointer"
            >
              <option value="">All Statuses ({complaints.length})</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="UNDER_REVIEW">Under Review</option>
              <option value="ASSIGNED">Assigned</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="RESOLVED">Resolved</option>
              <option value="DUPLICATE">Duplicate</option>
            </select>
          </div>
        </div>
      </div>

      {/* Complaints List */}
      <div className="space-y-4">
        {loading ? (
          <div className="p-12 text-center text-slate-400">Loading complaints...</div>
        ) : complaints.length === 0 ? (
          <div className="bg-white rounded-2xl border border-dashed border-slate-300 p-12 text-center space-y-3">
            <AlertCircle className="w-10 h-10 text-slate-400 mx-auto" />
            <h3 className="font-bold text-slate-700">No grievances found</h3>
            <p className="text-xs text-slate-500">Be the first to file a complaint in your locality.</p>
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="mt-2 inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-sky-600 text-white text-xs font-semibold cursor-pointer active:scale-95"
            >
              <PlusCircle className="w-4 h-4" />
              <span>File Grievance</span>
            </button>
          </div>
        ) : (
          complaints.map((c) => (
            <div
              key={c.id}
              className="bg-white rounded-2xl border border-slate-200 hover:border-sky-300 transition-all p-5 shadow-sm hover:shadow-md space-y-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="flex items-center space-x-2.5">
                  <span className="font-mono text-xs font-bold px-2.5 py-1 bg-slate-100 text-slate-800 rounded-lg">
                    {c.tracking_number}
                  </span>
                  <StatusBadge status={c.status} />
                  <PriorityBadge priority={c.priority} />
                  {c.is_duplicate && (
                    <span className="text-[11px] font-semibold bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded-full flex items-center">
                      <Layers className="w-3 h-3 mr-1" />
                      Merged (Similarity: {c.similarity_score ? parseInt(c.similarity_score * 100) : 85}%)
                    </span>
                  )}
                </div>

                <div className="text-xs text-slate-400 flex items-center space-x-1">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>{new Date(c.created_at).toLocaleDateString()}</span>
                </div>
              </div>

              {/* Title & Description */}
              <div>
                <h3 className="text-base font-bold text-slate-800">{c.title}</h3>
                <p className="text-sm text-slate-600 mt-1 leading-relaxed">{c.description}</p>
              </div>

              {/* Metadata Badges */}
              <div className="flex flex-wrap items-center gap-3 pt-2 text-xs text-slate-500">
                <div className="flex items-center space-x-1 text-slate-700 font-medium">
                  <span className="w-2 h-2 rounded-full bg-sky-500"></span>
                  <span>{c.category}</span>
                </div>

                {c.ward && (
                  <div className="flex items-center space-x-1 text-slate-600">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    <span>{c.ward}</span>
                  </div>
                )}

                {c.ai_confidence && (
                  <div className="flex items-center space-x-1 text-sky-700 font-medium bg-sky-50 px-2 py-0.5 rounded-md">
                    <Sparkles className="w-3 h-3 text-sky-500" />
                    <span>AI Confidence: {parseInt(c.ai_confidence * 100)}%</span>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal */}
      <FileComplaintModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onComplaintCreated={(newOne) => {
          setComplaints((prev) => [newOne, ...prev]);
        }}
      />
    </div>
  );
}
