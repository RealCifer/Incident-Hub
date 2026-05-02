import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { motion } from 'framer-motion';
import { ArrowLeft, Save, AlertTriangle, Info, Clock } from 'lucide-react';

export default function RcaForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    root_cause_category: 'Infrastructure',
    fix_applied: '',
    prevention_steps: '',
    start_time: '',
    end_time: '',
  });

  const categories = ['Infrastructure', 'Code Bug', 'Human Error', 'Network', 'Third Party', 'Security'];

  const calculateMTTR = () => {
    if (formData.start_time && formData.end_time) {
      const start = new Date(formData.start_time);
      const end = new Date(formData.end_time);
      const diff = (end - start) / 1000;
      if (diff > 0) {
        return (diff / 60).toFixed(1) + ' minutes';
      }
    }
    return '--';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      // Ensure ISO format with Z suffix for backend
      const payload = {
        ...formData,
        start_time: new Date(formData.start_time).toISOString(),
        end_time: new Date(formData.end_time).toISOString(),
      };
      await api.submitRca(id, payload);
      navigate(`/incident/${id}`);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to submit RCA');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 pb-20">
      <div className="flex items-center space-x-6">
        <Link to={`/incident/${id}`} className="p-2 rounded-full bg-slate-900 border border-slate-800 hover:border-slate-600 transition-colors">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h2 className="text-3xl font-black tracking-tight">Post-Mortem Analysis</h2>
          <p className="text-slate-500 text-sm mt-1">Submit Root Cause Analysis for Incident #{id.slice(0, 8)}</p>
        </div>
      </div>

      <motion.form 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        onSubmit={handleSubmit} 
        className="glass-card p-8 rounded-3xl space-y-8"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Category */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Root Cause Category</label>
            <select
              required
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 transition-colors text-slate-200"
              value={formData.root_cause_category}
              onChange={(e) => setFormData({ ...formData, root_cause_category: e.target.value })}
            >
              {categories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          {/* MTTR Preview */}
          <div className="p-4 rounded-xl bg-indigo-600/10 border border-indigo-600/20 flex items-center justify-between">
            <div className="flex items-center space-x-3 text-indigo-400">
              <Clock size={20} />
              <span className="text-xs font-bold uppercase tracking-widest">Estimated MTTR</span>
            </div>
            <div className="text-xl font-black text-indigo-400">{calculateMTTR()}</div>
          </div>
        </div>

        {/* Times */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Incident Start (UTC)</label>
            <input
              type="datetime-local"
              required
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 transition-colors text-slate-200"
              value={formData.start_time}
              onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Resolution Time (UTC)</label>
            <input
              type="datetime-local"
              required
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 transition-colors text-slate-200"
              value={formData.end_time}
              onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
            />
          </div>
        </div>

        {/* Fix Applied */}
        <div className="space-y-2">
          <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Fix Applied</label>
          <textarea
            required
            placeholder="Describe the technical steps taken to resolve the issue..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 transition-colors text-slate-200 min-h-[100px]"
            value={formData.fix_applied}
            onChange={(e) => setFormData({ ...formData, fix_applied: e.target.value })}
          />
        </div>

        {/* Prevention */}
        <div className="space-y-2">
          <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Prevention Steps</label>
          <textarea
            required
            placeholder="How will we prevent this from happening again? (e.g. better monitoring, code review, etc.)"
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 transition-colors text-slate-200 min-h-[100px]"
            value={formData.prevention_steps}
            onChange={(e) => setFormData({ ...formData, prevention_steps: e.target.value })}
          />
        </div>

        <div className="flex items-center justify-between pt-6 border-t border-slate-800">
           <div className="flex items-center space-x-2 text-slate-500 text-xs italic">
             <Info size={14} />
             <span>Submitting will allow transitioning the incident to CLOSED.</span>
           </div>
           <button
            type="submit"
            disabled={loading}
            className="flex items-center space-x-3 px-8 py-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl font-bold transition-all shadow-xl shadow-indigo-600/30 disabled:opacity-50"
          >
            <Save size={20} />
            <span>{loading ? 'Submitting...' : 'Finalize Analysis'}</span>
          </button>
        </div>
      </motion.form>
    </div>
  );
}
