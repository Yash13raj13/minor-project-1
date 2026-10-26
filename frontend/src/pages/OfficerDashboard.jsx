import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  CheckCircle, 
  XCircle, 
  Clock, 
  Sparkles,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { complaintAPI } from '../services/api';
import { StatusBadge, PriorityBadge } from '../components/Badges';

export default function OfficerDashboard() {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedComplaint, setSelectedComplaint] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [remarks, setRemarks] = useState('');
  const [updating, setUpdating] = useState(false);
  const [statusFilter, setStatusFilter] = useState('ALL');

  const fetchComplaints = async () => {
    try {
      setLoading(true);
      const data = await complaintAPI.list({ limit: 50 });
      setComplaints(data);
      if (data.length > 0) {
        setSelectedComplaint((prev) => {
          if (!prev) return data[0];
          return data.find(c => c.id === prev.id) || data[0];
        });
      }
    } catch (err) {
      console.error("Failed to fetch queue:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComplaints();
  }, []);

  useEffect(() => {
    if (selectedComplaint) {
      complaintAPI.getAudit(selectedComplaint.id)
        .then((logs) => setAuditLogs(logs || []))
        .catch(console.error);
    }
  }, [selectedComplaint]);

  const handleStatusTransition = async (newStatus) => {
    if (!selectedComplaint) return;
    setUpdating(true);
    try {
      const userRemarks = remarks.trim() || `Status updated to ${newStatus} by Zonal Officer`;
      const updated = await complaintAPI.updateStatus(
        selectedComplaint.id,
        newStatus,
        userRemarks
      );
      
      const nextList = complaints.map(c => c.id === updated.id ? updated : c);
      setComplaints(nextList);
      setSelectedComplaint(updated);
      setRemarks('');
      
      // Refresh audit trail
      const logs = await complaintAPI.getAudit(updated.id);
      setAuditLogs(logs || []);
    } catch (err) {
      alert("Failed to update status: " + (err.response?.data?.detail || err.message));
    } finally {
      setUpdating(false);
    }
  };

  const filteredComplaints = statusFilter === 'ALL'
    ? complaints
    : complaints.filter(c => c.status === statusFilter);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1 rounded-full w-fit mb-1.5">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Official Triaging & Resolution Desk</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Department Officer Workspace</h1>
          <p className="text-sm text-slate-500">Triage incoming civic grievances, verify AI categorization, and log resolution workflows.</p>
        </div>

        <button 
          onClick={fetchComplaints}
          disabled={loading}
          className="flex items-center space-x-2 px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-bold shadow-xs transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Queue</span>
        </button>
      </div>

      {/* Main Split Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Complaint Queue (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex justify-between items-center text-xs font-semibold text-slate-500 uppercase px-1">
            <span>Pending Triaging Queue ({filteredComplaints.length})</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs bg-slate-100 border border-slate-200 rounded-lg px-2 py-1 font-semibold text-slate-700"
            >
              <option value="ALL">All Status</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="ASSIGNED">Assigned</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="RESOLVED">Resolved</option>
            </select>
          </div>

          <div className="space-y-2.5 max-h-[750px] overflow-y-auto pr-1">
            {filteredComplaints.length === 0 ? (
              <div className="p-8 text-center bg-white rounded-xl border border-slate-200 text-xs text-slate-400">
                No tickets matching filter.
              </div>
            ) : (
              filteredComplaints.map((c) => {
                const isSelected = selectedComplaint?.id === c.id;
                return (
                  <div
                    key={c.id}
                    onClick={() => setSelectedComplaint(c)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-sky-50/80 border-sky-400 shadow-sm ring-1 ring-sky-400'
                        : 'bg-white border-slate-200 hover:border-slate-300 shadow-xs'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-mono text-xs font-bold text-slate-800">{c.tracking_number}</span>
                      <PriorityBadge priority={c.priority} />
                    </div>
                    <h4 className="text-sm font-bold text-slate-900 line-clamp-1">{c.title}</h4>
                    <p className="text-xs text-slate-500 line-clamp-2 mt-1">{c.description}</p>
                    
                    <div className="flex justify-between items-center pt-3 border-t border-slate-100 mt-3 text-[11px] text-slate-500">
                      <StatusBadge status={c.status} />
                      <span>{c.ward || 'General Zone'}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Selected Detail & Action Panel (7 cols) */}
        <div className="lg:col-span-7">
          {selectedComplaint ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
              {/* Header Info */}
              <div className="border-b border-slate-100 pb-4">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-sm font-bold bg-slate-100 text-slate-800 px-3 py-1 rounded-lg">
                      {selectedComplaint.tracking_number}
                    </span>
                    <StatusBadge status={selectedComplaint.status} />
                    <PriorityBadge priority={selectedComplaint.priority} />
                  </div>
                  <span className="text-xs text-slate-400">
                    Lodged: {new Date(selectedComplaint.created_at).toLocaleString()}
                  </span>
                </div>
                <h2 className="text-xl font-bold text-slate-900">{selectedComplaint.title}</h2>
                <p className="text-sm text-slate-600 mt-2 leading-relaxed">{selectedComplaint.description}</p>
              </div>

              {/* AI Classification & Duplicate Summary */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs">
                <div>
                  <span className="text-slate-400 block mb-0.5">Assigned Department</span>
                  <span className="font-bold text-slate-800 text-sm">{selectedComplaint.category}</span>
                  {selectedComplaint.ai_confidence && (
                    <span className="text-sky-600 font-semibold block mt-0.5 flex items-center">
                      <Sparkles className="w-3 h-3 mr-1" />
                      AI Confidence: {parseInt(selectedComplaint.ai_confidence * 100)}%
                    </span>
                  )}
                </div>

                <div>
                  <span className="text-slate-400 block mb-0.5">Location & Ward</span>
                  <span className="font-bold text-slate-800 text-sm">{selectedComplaint.ward || 'Central'}</span>
                  <span className="text-slate-500 block truncate mt-0.5">{selectedComplaint.address}</span>
                </div>
              </div>

              {/* Action Buttons for Status Change */}
              <div className="space-y-3 pt-2">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Officer Action & Resolution Remarks
                </label>
                <textarea
                  rows={2}
                  placeholder="Enter triaging remarks, field inspection notes, or resolution proof..."
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                />

                <div className="flex flex-wrap gap-2 pt-1">
                  <button
                    type="button"
                    disabled={updating}
                    onClick={() => handleStatusTransition('IN_PROGRESS')}
                    className="px-4 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 active:scale-95 text-white text-xs font-bold transition flex items-center space-x-1.5 cursor-pointer shadow-sm"
                  >
                    <Clock className="w-3.5 h-3.5" />
                    <span>Set In Progress</span>
                  </button>

                  <button
                    type="button"
                    disabled={updating}
                    onClick={() => handleStatusTransition('RESOLVED')}
                    className="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white text-xs font-bold transition flex items-center space-x-1.5 cursor-pointer shadow-sm"
                  >
                    <CheckCircle className="w-3.5 h-3.5" />
                    <span>Mark Resolved</span>
                  </button>

                  <button
                    type="button"
                    disabled={updating}
                    onClick={() => handleStatusTransition('REJECTED')}
                    className="px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 active:scale-95 text-white text-xs font-bold transition flex items-center space-x-1.5 cursor-pointer shadow-sm"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Reject / Invalid</span>
                  </button>
                </div>
              </div>

              {/* Audit Trail Timeline */}
              <div className="pt-4 border-t border-slate-100">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
                  Audit Trail & History
                </h4>
                <div className="space-y-3 border-l-2 border-slate-200 pl-4 ml-2">
                  {auditLogs.map((log) => (
                    <div key={log.id} className="relative text-xs space-y-1">
                      <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-sky-500 ring-4 ring-white" />
                      <div className="flex justify-between items-center text-slate-500">
                        <span className="font-bold text-slate-800">{log.action}</span>
                        <span>{new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      <p className="text-slate-600">{log.remarks}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center text-slate-400 bg-white rounded-2xl border border-slate-200">
              Select a grievance from the left queue to view details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
