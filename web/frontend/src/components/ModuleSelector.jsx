import React from 'react'
import { BarChart3, Bot, BookOpen } from 'lucide-react'

const modules = [
  {
    id: 'data_drift',
    icon: BarChart3,
    title: 'Data Drift',
    desc: 'Detect statistical drift between reference and production data using PSI, KS-Test, JS Divergence & Evidently.',
    color: 'blue',
    ready: true,
  },
  {
    id: 'model_drift',
    icon: Bot,
    title: 'Model Drift',
    desc: 'Monitor model performance degradation, prediction bias, and accuracy decay over time.',
    color: 'purple',
    ready: false,
  },
  {
    id: 'rag',
    icon: BookOpen,
    title: 'RAG Hallucination',
    desc: 'Detect hallucinations, faithfulness failures, and context gaps in LLM RAG pipelines.',
    color: 'emerald',
    ready: false,
  },
]

const colorMap = {
  blue:    { border: 'border-blue-500',   iconBg: 'bg-blue-100',   icon: 'text-blue-600',   ring: 'ring-blue-200' },
  purple:  { border: 'border-purple-400', iconBg: 'bg-purple-100', icon: 'text-purple-600', ring: 'ring-purple-200' },
  emerald: { border: 'border-emerald-400',iconBg: 'bg-emerald-100',icon: 'text-emerald-600',ring: 'ring-emerald-200' },
}

export default function ModuleSelector({ active, onSelect }) {
  return (
    <div>
      <p className="text-sm text-slate-500 mb-4 font-medium uppercase tracking-wider">Select Observability Module</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {modules.map((mod) => {
          const isActive = active === mod.id
          const c = colorMap[mod.color]
          const Icon = mod.icon
          return (
            <button
              key={mod.id}
              onClick={() => onSelect(mod.id)}
              disabled={!mod.ready}
              className={`
                relative text-left w-full p-5 rounded-2xl border-2 bg-white shadow-sm
                transition-all duration-200 group
                ${isActive ? `${c.border} ring-4 ${c.ring} shadow-md` : 'border-slate-200 hover:border-slate-300 hover:shadow-md'}
                ${!mod.ready ? 'opacity-70 cursor-not-allowed' : 'cursor-pointer'}
              `}
            >
              {!mod.ready && (
                <span className="absolute top-4 right-4 bg-amber-100 text-amber-700 text-xs font-semibold px-2.5 py-0.5 rounded-full">
                  Coming Soon
                </span>
              )}
              <div className={`inline-flex p-2.5 rounded-xl mb-3 ${c.iconBg}`}>
                <Icon size={22} className={c.icon} />
              </div>
              <h3 className="font-semibold text-slate-800 text-base mb-1">{mod.title}</h3>
              <p className="text-slate-500 text-sm leading-relaxed">{mod.desc}</p>
            </button>
          )
        })}
      </div>
    </div>
  )
}
