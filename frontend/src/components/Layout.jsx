import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, ShieldAlert, Activity, Settings, Bell } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export function Layout({ children }) {
  const location = useLocation();

  const navItems = [
    { name: 'Dashboard', icon: LayoutDashboard, path: '/' },
  ];

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-50">
      {/* Sidebar */}
      <aside className="w-64 glass-card border-r border-slate-800 flex flex-col">
        <div className="p-6 flex items-center space-x-3">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <ShieldAlert className="text-white" size={24} />
          </div>
          <span className="font-bold text-xl tracking-tight">IncidentHub</span>
        </div>

        <nav className="flex-1 px-4 py-4 space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                location.pathname === item.path
                  ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-600/30'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
              }`}
            >
              <item.icon size={20} />
              <span className="font-medium">{item.name}</span>
            </Link>
          ))}
        </nav>

        <div className="p-4 mt-auto border-t border-slate-800">
          <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800/50">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-500 uppercase tracking-widest font-bold">System Status</span>
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
            </div>
            <div className="text-sm font-medium">All Systems Operational</div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        <header className="h-20 glass-card border-b border-slate-800 flex items-center justify-between px-8 z-10">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-bold capitalize">
              {location.pathname === '/' ? 'Active Incidents' : location.pathname.split('/')[1]}
            </h1>
          </div>
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2 text-slate-400 text-sm">
              <Activity size={16} />
              <span>Auto-refreshing (5s)</span>
            </div>
            <button className="p-2 text-slate-400 hover:text-white transition-colors relative">
              <Bell size={20} />
              <span className="absolute top-1 right-1 w-2 h-2 bg-indigo-500 rounded-full border-2 border-slate-950" />
            </button>
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center font-bold text-sm border-2 border-slate-800">
              JD
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-auto p-8 relative">
           <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="max-w-7xl mx-auto h-full"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
