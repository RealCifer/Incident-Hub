import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ArrowLeft, 
  Terminal, 
  History, 
  PlayCircle, 
  CheckCircle2, 
  FileText,
  AlertTriangle,
  ExternalLink
} from 'lucide-react';

export default function IncidentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [workItem, setWorkItem] = useState(null);
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchData = async () => {
    try {
      const [wiRes, sigRes] = await Promise.all([
        api.getWorkItem(id),
        api.getSignals(id)
      ]);
      setWorkItem(wiRes.data);
      setSignals(sigRes.data);
    } catch (err) {
      console.error('Error fetching detail:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const timer = setInterval(fetchData, 5000);
    return () => clearInterval(timer);
  }, [id]);

  const handleTransition = async (targetState) => {
    setActionLoading(true);
    try {
      await api.transitionWorkItem(id, targetState);
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Transition failed');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading && !workItem) {
    return <div className="flex items-center justify-center h-full text-slate-500">Initializing detail view...</div>;
  }

  const nextStateMap = {
    OPEN: 'INVESTIGATING',
    INVESTIGATING: 'RESOLVED',
    RESOLVED: 'CLOSED',
  };

  const nextState = nextStateMap[workItem.state];

  return (
    <div className="space-y-8 pb-20">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <Link to="/" className="p-2 rounded-full bg-slate-900 border border-slate-800 hover:border-slate-600 transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <div className="text-xs font-mono text-slate-500 mb-1">INCIDENT-ID: {id}</div>
            <h2 className="text-3xl font-black tracking-tight">{workItem.component_id} Component Outage</h2>
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          {nextState && (
            <button
              onClick={() => handleTransition(nextState)}
              disabled={actionLoading || (workItem.state === 'RESOLVED' && !workItem.rca)}
              className={`flex items-center space-x-2 px-6 py-2.5 rounded-xl font-bold transition-all ${
                workItem.state === 'RESOLVED' && !workItem.rca
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30'
              }`}
            >
              {actionLoading ? 'Updating...' : `Move to ${nextState}`}
            </button>
          )}
          {workItem.state === 'RESOLVED' && !workItem.rca && (
             <Link
              to={`/rca/${id}`}
              className="flex items-center space-x-2 px-6 py-2.5 rounded-xl font-bold bg-amber-600 hover:bg-amber-500 text-white shadow-lg shadow-amber-600/30 transition-all"
            >
              <FileText size={18} />
              <span>Submit RCA</span>
            </Link>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Summary */}
        <div className="lg:col-span-1 space-y-6">
           <div className="glass-card p-6 rounded-3xl space-y-6">
              <div>
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Lifecycle Status</h3>
                <div className="flex items-center space-x-4">
                  <div className={`w-3 h-3 rounded-full animate-pulse ${
                    workItem.state === 'OPEN' ? 'bg-rose-500' : 'bg-emerald-500'
                  }`} />
                  <span className="text-xl font-bold">{workItem.state}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                 <div className="p-4 rounded-2xl bg-slate-900/50 border border-slate-800/50">
                    <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1">Severity</div>
                    <div className={`font-bold ${
                      workItem.severity === 'CRITICAL' ? 'text-rose-500' : 'text-amber-500'
                    }`}>{workItem.severity}</div>
                 </div>
                 <div className="p-4 rounded-2xl bg-slate-900/50 border border-slate-800/50">
                    <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1">Signals</div>
                    <div className="font-bold text-slate-200">{signals.length}</div>
                 </div>
              </div>

              {workItem.rca && (
                <div className="p-5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20">
                  <div className="flex items-center text-emerald-400 font-bold mb-2 space-x-2 text-sm uppercase tracking-wider">
                    <CheckCircle2 size={16} />
                    <span>RCA Completed</span>
                  </div>
                  <div className="text-xs text-slate-400 mb-3">MTTR: {(workItem.rca.mttr_seconds / 60).toFixed(1)} minutes</div>
                  <button className="w-full py-2 bg-slate-900 rounded-lg text-xs font-bold hover:bg-slate-800 transition-colors">
                    View Full Analysis
                  </button>
                </div>
              )}
           </div>

           <div className="glass-card p-6 rounded-3xl">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Timeline</h3>
              <div className="space-y-4">
                {[
                  { label: 'Incident Created', time: workItem.created_at, icon: AlertTriangle, color: 'text-rose-500' },
                  { label: 'Last Activity', time: workItem.updated_at, icon: History, color: 'text-indigo-400' },
                ].map((step) => (
                  <div key={step.label} className="flex items-start space-x-3">
                    <div className={`p-1.5 rounded-lg bg-slate-900 ${step.color} border border-slate-800`}>
                      <step.icon size={14} />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-300">{step.label}</div>
                      <div className="text-[10px] text-slate-500">{new Date(step.time).toLocaleString()}</div>
                    </div>
                  </div>
                ))}
              </div>
           </div>
        </div>

        {/* Right Column: Signals */}
        <div className="lg:col-span-2 space-y-6">
           <div className="glass-card rounded-3xl overflow-hidden flex flex-col h-full min-h-[500px]">
              <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-900/20">
                <div className="flex items-center space-x-3">
                  <Terminal size={20} className="text-indigo-400" />
                  <h3 className="font-bold">Raw Signal Logs</h3>
                </div>
                <div className="text-xs text-slate-500 font-mono">Real-time ingestion active</div>
              </div>
              
              <div className="flex-1 overflow-auto p-4 space-y-3 font-mono text-sm">
                <AnimatePresence initial={false}>
                  {signals.map((sig, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="p-3 rounded-xl bg-slate-950/50 border border-slate-900 hover:border-slate-800 transition-colors group"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-indigo-500 font-bold">SIGNAL://{sig.component_id}</span>
                        <span className="text-slate-600 text-[10px]">{new Date(sig.timestamp || Date.now()).toLocaleTimeString()}</span>
                      </div>
                      <pre className="text-slate-400 text-xs overflow-x-auto">
                        {JSON.stringify(sig.payload, null, 2)}
                      </pre>
                    </motion.div>
                  ))}
                </AnimatePresence>
                {signals.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-full text-slate-600 space-y-4 py-20">
                    <History size={48} className="opacity-20" />
                    <div>Waiting for signals to propagate...</div>
                  </div>
                )}
              </div>
           </div>
        </div>
      </div>
    </div>
  );
}
