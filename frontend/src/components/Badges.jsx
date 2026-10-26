import React from 'react';

export function StatusBadge({ status }) {
  const map = {
    SUBMITTED: { bg: 'bg-blue-50 text-blue-700 border-blue-200', label: 'Submitted' },
    UNDER_REVIEW: { bg: 'bg-indigo-50 text-indigo-700 border-indigo-200', label: 'Under Review' },
    ASSIGNED: { bg: 'bg-amber-50 text-amber-700 border-amber-200', label: 'Assigned' },
    IN_PROGRESS: { bg: 'bg-sky-50 text-sky-700 border-sky-200', label: 'In Progress' },
    RESOLVED: { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: 'Resolved' },
    REJECTED: { bg: 'bg-rose-50 text-rose-700 border-rose-200', label: 'Rejected' },
    DUPLICATE: { bg: 'bg-purple-50 text-purple-700 border-purple-200', label: 'Duplicate Flagged' },
  };

  const current = map[status] || { bg: 'bg-slate-100 text-slate-700 border-slate-200', label: status };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${current.bg}`}>
      {current.label}
    </span>
  );
}

export function PriorityBadge({ priority }) {
  const map = {
    LOW: { bg: 'bg-slate-100 text-slate-700 border-slate-200', label: 'Low' },
    MEDIUM: { bg: 'bg-amber-50 text-amber-700 border-amber-200', label: 'Medium' },
    HIGH: { bg: 'bg-orange-50 text-orange-700 border-orange-200', label: 'High' },
    CRITICAL: { bg: 'bg-rose-100 text-rose-800 border-rose-300 font-bold animate-pulse', label: 'CRITICAL' },
  };

  const current = map[priority] || { bg: 'bg-slate-100 text-slate-700 border-slate-200', label: priority };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${current.bg}`}>
      {current.label}
    </span>
  );
}

