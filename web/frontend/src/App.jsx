import React, { useState } from 'react'
import Navbar from './components/Navbar'
import ModuleSelector from './components/ModuleSelector'
import DataDriftPage from './pages/DataDriftPage'

export default function App() {
  const [activeModule, setActiveModule] = useState('data_drift')

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ModuleSelector active={activeModule} onSelect={setActiveModule} />
        <div className="mt-6">
          {activeModule === 'data_drift' && <DataDriftPage />}
          {activeModule === 'model_drift' && (
            <ComingSoon title="Model Drift" desc="Monitor model performance degradation, prediction bias, and accuracy decay over time." />
          )}
          {activeModule === 'rag' && (
            <ComingSoon title="RAG Hallucination" desc="Detect hallucinations, faithfulness failures, and context gaps in LLM RAG pipelines." />
          )}
        </div>
      </main>
    </div>
  )
}

function ComingSoon({ title, desc }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-16 text-center shadow-sm">
      <div className="text-5xl mb-4">🚧</div>
      <h2 className="text-2xl font-semibold text-slate-800 mb-2">{title}</h2>
      <p className="text-slate-500 max-w-md mx-auto">{desc}</p>
      <span className="mt-4 inline-block bg-amber-100 text-amber-700 text-sm font-medium px-3 py-1 rounded-full">Coming Soon</span>
    </div>
  )
}
