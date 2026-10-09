import React, { useState } from 'react'
import { FileSpreadsheet, Server, Zap } from 'lucide-react'
import CsvBatchTab from '../components/CsvBatchTab'
import ApiIntegrationTab from '../components/ApiIntegrationTab'
import LiveRiverSimulationTab from '../components/LiveRiverSimulationTab'

const tabs = [
  { id: 'csv', label: 'Option 1: CSV File Upload (Batch)', icon: FileSpreadsheet },
  { id: 'api', label: 'Option 2: Application API Integration', icon: Server },
  { id: 'river', label: 'Option 3: Live Real-Time River Simulation', icon: Zap },
]

export default function DataDriftPage() {
  const [activeTab, setActiveTab] = useState('csv')

  return (
    <div className="space-y-6">
      {/* Sub-navigation tabs */}
      <div className="bg-white rounded-2xl border border-slate-200 p-2 shadow-sm flex flex-wrap gap-2">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2.5 px-4 py-2.5 rounded-xl font-medium text-sm transition-all cursor-pointer ${
                isActive
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Icon size={18} />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab Panels */}
      {activeTab === 'csv' && <CsvBatchTab />}
      {activeTab === 'api' && <ApiIntegrationTab />}
      {activeTab === 'river' && <LiveRiverSimulationTab />}
    </div>
  )
}
