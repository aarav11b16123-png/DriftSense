import React, { useState } from 'react'
import {
  AlertTriangle,
  CheckCircle,
  FileDown,
  FileText,
  Download,
  ChevronDown,
  ChevronUp,
  Wrench,
  HelpCircle
} from 'lucide-react'
import DistributionChart from './DistributionChart'

export default function RcaReportView({ incident, refData, curData, onDownloadPdf, onDownloadMd, onDownloadJson }) {
  const [expandedFeatures, setExpandedFeatures] = useState({})

  if (!incident) return null

  const toggleExpand = (itemId) => {
    setExpandedFeatures((prev) => ({
      ...prev,
      [itemId]: !prev[itemId],
    }))
  }

  const sevColors = {
    MAJOR: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', badge: 'bg-red-600 text-white' },
    DATA_QUALITY: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', badge: 'bg-amber-500 text-white' },
    MODERATE: { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200', badge: 'bg-yellow-500 text-slate-900' },
    NONE: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', badge: 'bg-emerald-600 text-white' },
  }

  const currentSev = sevColors[incident.severity] || sevColors.NONE

  return (
    <div className="space-y-6 pt-2 animate-fadeIn">
      {/* Executive Summary Card */}
      <div className={`p-6 rounded-2xl border ${currentSev.border} ${currentSev.bg} shadow-sm`}>
        <div className="flex flex-wrap items-center justify-between gap-4 mb-3">
          <div className="flex items-center gap-3">
            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${currentSev.badge}`}>
              Severity: {incident.severity}
            </span>
            <span className="text-xs text-slate-500">Incident ID: {incident.incident_id?.slice(0, 8)}</span>
          </div>
          <span className="text-xs text-slate-500">{new Date(incident.created_at).toLocaleString()}</span>
        </div>
        <h3 className="text-lg font-bold text-slate-900 mb-1">Root Cause Analysis Findings</h3>
        <p className="text-slate-700 text-sm leading-relaxed">{incident.summary}</p>

        {incident.metrics && (
          <div className="mt-4 flex flex-wrap gap-4 pt-3 border-t border-slate-200/60">
            {Object.entries(incident.metrics).map(([k, v]) => (
              <div key={k} className="text-xs">
                <span className="text-slate-500 font-medium capitalize">{k.replace(/_/g, ' ')}:</span>{' '}
                <span className="text-slate-900 font-bold">{typeof v === 'number' ? v.toFixed(3) : String(v)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Dataset-level causes */}
      {incident.dataset_level_causes && incident.dataset_level_causes.length > 0 && (
        <div className="p-5 rounded-2xl border border-red-200 bg-red-50/70">
          <div className="flex items-center gap-2.5 text-red-800 font-bold text-base mb-2">
            <AlertTriangle size={20} className="text-red-600" />
            Dataset-Level Population Shift Detected
          </div>
          <div className="space-y-3">
            {incident.dataset_level_causes.map((cause, idx) => (
              <div key={idx} className="bg-white/80 p-4 rounded-xl border border-red-100 text-sm">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold text-slate-900">{cause.label}</span>
                  <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-800">
                    Confidence: {(cause.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <p className="text-slate-600 text-xs mb-2">
                  Evidence: {JSON.stringify(cause.evidence)}
                </p>
                <div className="flex items-center gap-1.5 text-xs text-blue-700 font-medium bg-blue-50 p-2 rounded-lg">
                  <Wrench size={14} />
                  <span>Recommended Action: {cause.recommended_action}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Feature Level Findings */}
      <div>
        <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3">
          Feature-Level Probable Causes ({incident.findings?.length || 0} Affected)
        </h4>

        {(!incident.findings || incident.findings.length === 0) ? (
          <div className="bg-white p-8 text-center rounded-2xl border border-slate-200 text-slate-500 text-sm">
            <CheckCircle className="mx-auto text-emerald-500 mb-2" size={32} />
            No features with statistically significant drift causes detected.
          </div>
        ) : (
          <div className="space-y-4">
            {incident.findings.map((finding) => {
              const isExpanded = expandedFeatures[finding.item_id] !== false // Default expanded or collapsible
              const refValues = refData ? refData[finding.item_id] : []
              const curValues = curData ? curData[finding.item_id] : []

              return (
                <div
                  key={finding.item_id}
                  className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden transition-all"
                >
                  {/* Card Header / Toggle */}
                  <div
                    onClick={() => toggleExpand(finding.item_id)}
                    className="p-5 flex items-center justify-between cursor-pointer hover:bg-slate-50/80 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-xl ${finding.verdict === 'DRIFT_EXPLAINED' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                        <AlertTriangle size={18} />
                      </div>
                      <div>
                        <h5 className="font-bold text-slate-900 text-base">{finding.item_id}</h5>
                        <p className="text-xs text-slate-500">{finding.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${finding.verdict === 'DRIFT_EXPLAINED' ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}`}>
                        {finding.verdict}
                      </span>
                      {isExpanded ? <ChevronUp size={18} className="text-slate-400" /> : <ChevronDown size={18} className="text-slate-400" />}
                    </div>
                  </div>

                  {/* Expanded Body */}
                  {isExpanded && (
                    <div className="p-5 pt-0 border-t border-slate-100 space-y-5 bg-slate-50/40">
                      {/* Ranked Causes */}
                      <div className="mt-4 space-y-3">
                        <h6 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          Ranked Probable Causes (with Evidence)
                        </h6>
                        {finding.causes.map((cause, cIdx) => (
                          <div key={cIdx} className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-2">
                            <div className="flex justify-between items-center">
                              <span className="font-bold text-slate-800 text-sm">{cause.label}</span>
                              <span className="text-xs font-bold text-blue-600">
                                Confidence: {(cause.confidence * 100).toFixed(0)}%
                              </span>
                            </div>

                            {/* Progress bar */}
                            <div className="w-full bg-slate-100 rounded-full h-2">
                              <div
                                className="bg-blue-600 h-2 rounded-full transition-all"
                                style={{ width: `${Math.min(cause.confidence * 100, 100)}%` }}
                              />
                            </div>

                            {/* Evidence details */}
                            <div className="bg-slate-50 p-2.5 rounded-lg text-xs space-y-1 text-slate-600">
                              <span className="font-semibold text-slate-700 block">Quantitative Evidence:</span>
                              {Object.entries(cause.evidence || {}).map(([k, v]) => (
                                <div key={k} className="flex justify-between">
                                  <span className="text-slate-500">{k}:</span>
                                  <span className="font-mono text-slate-800 font-medium">
                                    {typeof v === 'number' ? v.toFixed(4) : String(v)}
                                  </span>
                                </div>
                              ))}
                            </div>

                            {/* Recommended Action */}
                            <div className="flex items-start gap-2 text-xs bg-emerald-50 text-emerald-900 p-2.5 rounded-lg border border-emerald-100 font-medium">
                              <Wrench size={14} className="mt-0.5 text-emerald-600 shrink-0" />
                              <span>Action: {cause.recommended_action}</span>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Distribution Histogram Overlay */}
                      {refValues && curValues && refValues.length > 0 && (
                        <DistributionChart featureName={finding.item_id} refData={refValues} curData={curValues} />
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Download Action Center */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <h5 className="font-bold text-slate-900 text-sm">Export Structured Audit Reports</h5>
          <p className="text-xs text-slate-500">Download deterministic RCA reports for documentation and audit trails</p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={onDownloadMd}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors cursor-pointer"
          >
            <FileText size={14} />
            Markdown (.md)
          </button>
          <button
            onClick={onDownloadJson}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors cursor-pointer"
          >
            <FileDown size={14} />
            JSON (.json)
          </button>
          <button
            onClick={onDownloadPdf}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 shadow-sm transition-colors cursor-pointer"
          >
            <Download size={14} />
            Download PDF Report
          </button>
        </div>
      </div>
    </div>
  )
}
