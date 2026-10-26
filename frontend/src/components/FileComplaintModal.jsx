import React, { useState, useEffect } from 'react';
import { 
  X, 
  Sparkles, 
  AlertTriangle, 
  CheckCircle2, 
  MapPin, 
  Send,
  Loader2
} from 'lucide-react';
import { aiAPI, complaintAPI } from '../services/api';

const WARDS = [
  'Ward 3 - East',
  'Ward 7 - Central',
  'Ward 9 - South',
  'Ward 12 - North',
  'Ward 15 - West',
];

export default function FileComplaintModal({ isOpen, onClose, onComplaintCreated }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('Roads & Infrastructure');
  const [ward, setWard] = useState('Ward 7 - Central');
  const [address, setAddress] = useState('');
  const [loading, setLoading] = useState(false);
  const [aiAnalyzing, setAiAnalyzing] = useState(false);

  // Duplicate candidate warning state
  const [duplicateMatches, setDuplicateMatches] = useState([]);
  const [aiSuggestion, setAiSuggestion] = useState(null);

  // Debounced duplicate detection
  useEffect(() => {
    if (title.length < 4 && description.length < 8) {
      setDuplicateMatches([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const res = await aiAPI.checkDuplicates(title, description);
        if (res && res.is_duplicate) {
          setDuplicateMatches(res.candidates || []);
        } else {
          setDuplicateMatches([]);
        }
      } catch (err) {
        console.warn("Duplicate check:", err);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [title, description]);

  const handleAiAutoCategorize = async () => {
    if (!title && !description) {
      alert("Please enter a summary title or description first to auto-classify.");
      return;
    }
    setAiAnalyzing(true);
    try {
      const res = await aiAPI.classify(title, description);
      setAiSuggestion(res);
      if (res && res.category) {
        setCategory(res.category);
      }
    } catch (err) {
      console.warn("AI Categorization:", err);
    } finally {
      setAiAnalyzing(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      alert("Please fill in both title and description.");
      return;
    }

    setLoading(true);
    try {
      const lat = 28.6139 + (Math.random() - 0.5) * 0.04;
      const lon = 77.2090 + (Math.random() - 0.5) * 0.04;

      const payload = {
        title: title.trim(),
        description: description.trim(),
        category,
        ward,
        address: address.trim() || `${ward}, Civic Area`,
        latitude: lat,
        longitude: lon,
      };

      const newComplaint = await complaintAPI.create(payload);
      if (onComplaintCreated) {
        onComplaintCreated(newComplaint);
      }
      onClose();
    } catch (err) {
      console.error("Submit error:", err);
      alert("Failed to lodge complaint: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full border border-slate-100 overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="bg-slate-900 px-6 py-4 flex items-center justify-between text-white">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-sky-500/20 text-sky-400 flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-lg">Lodge Grievance with CivicLens</h3>
              <p className="text-xs text-slate-400">AI automatically classifies category & detects duplicates</p>
            </div>
          </div>
          <button 
            type="button"
            onClick={onClose} 
            className="text-slate-400 hover:text-white transition p-1 rounded-lg hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Title */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Grievance Summary / Title *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Broken water pipe flooding road junction"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>

          {/* Description */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Detailed Description *
              </label>
              <button
                type="button"
                onClick={handleAiAutoCategorize}
                disabled={aiAnalyzing}
                className="text-xs font-semibold text-sky-600 hover:text-sky-700 flex items-center px-2 py-0.5 rounded-lg hover:bg-sky-50 transition"
              >
                {aiAnalyzing ? (
                  <Loader2 className="w-3 h-3 animate-spin mr-1" />
                ) : (
                  <Sparkles className="w-3 h-3 mr-1 text-sky-500" />
                )}
                AI Auto-Classify
              </button>
            </div>
            <textarea
              required
              rows={3}
              placeholder="Provide exact details, street landmarks, severity, and any imminent hazards..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>

          {/* AI Suggestion Banner */}
          {aiSuggestion && (
            <div className="p-3 bg-sky-50 border border-sky-200 rounded-xl flex items-start space-x-2 text-xs text-sky-900">
              <CheckCircle2 className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold">AI Detection:</span> Suggested Department:{' '}
                <span className="font-bold">{aiSuggestion.category}</span> ({parseInt(aiSuggestion.confidence * 100)}% confidence). Urgency calculated as{' '}
                <span className="font-bold text-amber-700">{aiSuggestion.priority}</span>.
              </div>
            </div>
          )}

          {/* Real-time FAISS Duplicate Warning */}
          {duplicateMatches.length > 0 && (
            <div className="p-3.5 bg-purple-50 border border-purple-200 rounded-xl space-y-2">
              <div className="flex items-center space-x-2 text-xs font-bold text-purple-900">
                <AlertTriangle className="w-4 h-4 text-purple-600" />
                <span>FAISS Semantic Duplicate Alert ({duplicateMatches.length} Similar Issue Found)</span>
              </div>
              <p className="text-xs text-purple-800">
                A similar grievance already exists nearby. Your submission will be linked to prevent duplicate city crew dispatches:
              </p>
              <div className="space-y-1.5">
                {duplicateMatches.map((item) => (
                  <div key={item.complaint_id} className="bg-white p-2.5 rounded-lg border border-purple-100 text-xs">
                    <div className="flex justify-between items-center text-slate-800 font-medium">
                      <span>{item.tracking_number} - {item.title}</span>
                      <span className="bg-purple-100 text-purple-700 px-2 py-0.5 rounded font-bold">
                        {parseInt(item.similarity_score * 100)}% Match
                      </span>
                    </div>
                    <p className="text-slate-500 text-[11px] truncate mt-0.5">{item.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Ward & Category Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Ward / Zone *
              </label>
              <select
                value={ward}
                onChange={(e) => setWard(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                {WARDS.map((w) => (
                  <option key={w} value={w}>{w}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                <option value="Roads & Infrastructure">Roads & Infrastructure</option>
                <option value="Sanitation & Solid Waste">Sanitation & Solid Waste</option>
                <option value="Water Supply & Sewage">Water Supply & Sewage</option>
                <option value="Electricity & Street Lighting">Electricity & Street Lighting</option>
                <option value="Public Health & Environment">Public Health & Environment</option>
              </select>
            </div>
          </div>

          {/* Location Address */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Location Landmark / Address
            </label>
            <div className="relative">
              <input
                type="text"
                placeholder="e.g. Near Pillar 45, Main Ring Road Junction"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                className="w-full pl-9 pr-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
              <MapPin className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end space-x-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-slate-200 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 rounded-xl bg-sky-600 hover:bg-sky-700 text-white text-sm font-semibold flex items-center space-x-2 transition shadow-md disabled:opacity-50 active:scale-95 cursor-pointer"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              <span>Submit Grievance</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
