import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { motion } from 'framer-motion';
import { AlertCircle, Clock, ChevronRight, Filter } from 'lucide-react';

const SEVERITY_STYLES = {
  CRITICAL: 'bg-red-500/10 text-red-500 border-red-500/20 shadow-red-500/10',
  HIGH: 'bg-orange-500/10 text-orange-500 border-orange-500/20 shadow-orange-500/10',
  MEDIUM: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20 shadow-yellow-500/10',
  LOW: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20 shadow-emerald-500/10',
};

const STATE_COLORS = {
  OPEN: 'bg-rose-500',
  INVESTIGATING: 'bg-indigo-500',
  RESOLVED: 'bg-amber-500',
  CLOSED: 'bg-slate-500',
};

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboard = async () => {
    try {
      const res = await api.getDashboard();
      setData(res.data);
    } catch (err) {
      console.error('Failed to fetch dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
    const timer = setInterval(fetchDashboard, 5000);
    return () => clearInterval(timer);
  }, []);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-full">
        <motion.div 
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full"
        />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {[
          { label: 'Total Active', value: data.total_active, icon: Activity, color: 'text-indigo-400' },
          { label: 'Open', value: data.counts_by_state.OPEN || 0, icon: AlertCircle, color: 'text-rose-400' },
          { label: 'Investigating', value: data.counts_by_state.INVESTIGATING || 0, icon: Clock, color: 'text-indigo-400' },
          { label: 'Resolved', value: data.counts_by_state.RESOLVED || 0, icon: CheckCircle, color: 'text-amber-400' },
        ].map((stat, i) => (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            key={stat.label}
            className="glass-card p-6 rounded-2xl flex flex-col"
          >
            <div className="text-slate-400 text-sm font-medium mb-1">{stat.label}</div>
            <div className={`text-3xl font-bold ${stat.color}`}>{stat.value}</div>
          </motion.div>
        ))}
      </div>

      {/* Incident List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold">Active Incidents</h2>
          <button className="flex items-center space-x-2 px-4 py-2 bg-slate-800 rounded-lg hover:bg-slate-700 transition-colors text-sm font-medium border border-slate-700">
            <Filter size={16} />
            <span>Filter</span>
          </button>
        </div>

        {data.incidents.length === 0 ? (
          <div className="text-center py-20 glass-card rounded-3xl border-dashed border-slate-700">
            <div className="text-slate-500">No active incidents detected. Go grab a coffee! ☕</div>
          </div>
        ) : (
          <div className="grid gap-4">
            {data.incidents.map((incident, i) => (
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                key={incident.workitem_id}
              >
                <Link
                  to={`/incident/${incident.workitem_id}`}
                  className="glass-card p-5 rounded-2xl flex items-center group hover:bg-slate-800/80 transition-all duration-300 border border-slate-800/50 hover:border-slate-600/50"
                >
                  <div className={`w-1 h-12 rounded-full ${STATE_COLORS[incident.state]} mr-6 shadow-lg shadow-${STATE_COLORS[incident.state]}/20`} />
                  
                  <div className="flex-1">
                    <div className="flex items-center mb-1">
                      <span className={`px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase tracking-widest border ${SEVERITY_STYLES[incident.severity]}`}>
                        {incident.severity}
                      </span>
                      <span className="text-slate-500 text-xs ml-4 font-mono">#{incident.workitem_id.slice(0, 8)}</span>
                    </div>
                    <div className="text-lg font-bold text-slate-200 group-hover:text-white transition-colors">
                      {incident.component_id} Incident
                    </div>
                  </div>

                  <div className="flex flex-col items-end mr-8">
                    <div className="text-xs text-slate-500 font-medium mb-1 uppercase tracking-wider">Status</div>
                    <div className="text-sm font-bold text-slate-300">{incident.state}</div>
                  </div>

                  <div className="flex flex-col items-end mr-8 hidden md:flex">
                    <div className="text-xs text-slate-500 font-medium mb-1 uppercase tracking-wider">Reported</div>
                    <div className="text-sm font-medium text-slate-300">
                      {new Date(incident.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>

                  <div className="p-2 rounded-full bg-slate-800 group-hover:bg-indigo-600 group-hover:text-white transition-all duration-300 text-slate-500">
                    <ChevronRight size={20} />
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Missing imports in previous blocks
import { Activity, CheckCircle } from 'lucide-react';
