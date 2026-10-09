import React from 'react'
import { Activity } from 'lucide-react'

export default function Navbar() {
  return (
    <nav className="bg-slate-900 shadow-lg sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-1.5 rounded-lg">
              <Activity size={20} className="text-white" />
            </div>
            <div>
              <span className="text-white font-bold text-xl tracking-tight">DriftSense</span>
              <span className="ml-2 text-slate-400 text-xs font-medium hidden sm:inline">Enterprise AI Observability Platform</span>
            </div>
          </div>
          {/* Right side */}
          <div className="flex items-center gap-6">
            <span className="hidden md:flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
              <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse"></span>
              System Online
            </span>
            <span className="text-slate-400 text-sm hidden md:block">v1.0.0</span>
          </div>
        </div>
      </div>
    </nav>
  )
}
