import React, { useState } from 'react'
import axios from 'axios'
import {
  UploadCloud,
  FileSpreadsheet,
  Play,
  Search,
  CheckCircle2,
  AlertCircle,
  PieChart as PieIcon,
  BarChart2
} from 'lucide-react'
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid
} from 'recharts'
import RcaReportView from './RcaReportView'

export default function CsvBatchTab() {
  const [refFile, setRefFile] = useState(null)
  const [curFile, setCurFile] = useState(null)
  const [refPreview, setRefPreview] = useState([])
  const [curPreview, setCurPreview] = useState([])
  const [refColumns, setRefColumns] = useState([])
  const [curColumns, setCurColumns] = useState([])
  const [refRawData, setRefRawData] = useState({})
  const [curRawData, setCurRawData] = useState({})

  const [loadingDrift, setLoadingDrift] = useState(false)
  const [driftReport, setDriftReport] = useState(null)

  const [loadingRca, setLoadingRca] = useState(false)
  const [rcaIncident, setRcaIncident] = useState(null)

  const parseCsvPreview = (file, setPreview, setCols, setRaw) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const text = e.target.result
      const lines = text.split(/\r\n|\n/).filter((l) => l.trim() !== '')
      if (lines.length > 0) {
        const headers = lines[0].split(',').map((h) => h.trim().replace(/^"|"$/g, ''))
        setCols(headers)

        const rows = lines.slice(1, 4).map((line) => {
          const vals = line.split(',').map((v) => v.trim().replace(/^"|"$/g, ''))
          const rowObj = {}
          headers.forEach((h, i) => {
            rowObj[h] = vals[i] || ''
          })
          return rowObj
        })
        setPreview(rows)

        // Parse column-wise numeric arrays for charts (up to 1000 rows)
        const colMap = {}
        headers.forEach((h) => (colMap[h] = []))
        lines.slice(1, 1001).forEach((line) => {
          const vals = line.split(',')
          headers.forEach((h, i) => {
            const num = parseFloat(vals[i])
            if (!isNaN(num)) {
              colMap[h].push(num)
            }
          })
        })
        setRaw(colMap)
      }
    }
    reader.readAsText(file)
  }

  const handleRefUpload = (e) => {
    const file = e.target.files[0]
    if (file) {
      setRefFile(file)
      parseCsvPreview(file, setRefPreview, setRefColumns, setRefRawData)
      setDriftReport(null)
      setRcaIncident(null)
    }
  }

  const handleCurUpload = (e) => {
    const file = e.target.files[0]
    if (file) {
      setCurFile(file)
      parseCsvPreview(file, setCurPreview, setCurColumns, setCurRawData)
      setDriftReport(null)
      setRcaIncident(null)
    }
  }

  const handleRunDrift = async () => {
    if (!refFile || !curFile) return
    setLoadingDrift(true)
    setRcaIncident(null)

    const formData = new FormData()
    formData.append('reference', refFile)
    formData.append('current', curFile)

    try {
      const res = await axios.post('/api/drift', formData)
      setDriftReport(res.data)
    } catch (err) {
      alert('Error running drift detection: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoadingDrift(false)
    }
  }

  const handleRunRca = async () => {
    if (!refFile || !curFile) return
    setLoadingRca(true)

    const formData = new FormData()
    formData.append('reference', refFile)
    formData.append('current', curFile)

    try {
      const res = await axios.post('/api/rca', formData)
      setRcaIncident(res.data)
    } catch (err) {
      alert('Error running RCA: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoadingRca(false)
    }
  }

  const downloadFile = async (endpoint, filename, type) => {
    if (!refFile || !curFile) return
    const formData = new FormData()
    formData.append('reference', refFile)
    formData.append('current', curFile)

    try {
      const res = await axios.post(endpoint, formData, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data], { type }))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (err) {
      alert('Error downloading report: ' + err.message)
    }
  }

  // Chart data calculations
  const stats = driftReport?.column_level_stats || {}
  const featureNames = Object.keys(stats)
  const psiChartData = featureNames.map((col) => {
    const psiVal = stats[col]?.PSI?.value || 0
    return {
      feature: col,
      PSI: Number(psiVal.toFixed(4)),
      fill: psiVal > 0.25 ? '#ef4444' : psiVal > 0.1 ? '#f59e0b' : '#10b981',
    }
  })

  const shareDrift = driftReport?.evidently_overall?.share_of_drifted_columns || 0
  const driftedCount = Math.round(shareDrift * featureNames.length)
  const stableCount = featureNames.length - driftedCount
  const pieData = [
    { name: 'Drifted', value: driftedCount, fill: '#ef4444' },
    { name: 'Stable', value: stableCount, fill: '#10b981' },
  ]

  return (
    <div className="space-y-6">
      {/* File Upload Zone */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Reference Upload */}
        <div className="bg-white p-6 rounded-2xl border-2 border-dashed border-slate-200 hover:border-blue-400 transition-all text-center relative group">
          <input
            type="file"
            accept=".csv"
            onChange={handleRefUpload}
            className="absolute inset-0 opacity-0 cursor-pointer w-full h-full z-10"
          />
          <div className="flex flex-col items-center justify-center pointer-events-none">
            <div className="p-3 bg-blue-50 text-blue-600 rounded-xl mb-3 group-hover:scale-110 transition-transform">
              <UploadCloud size={24} />
            </div>
            <h4 className="font-bold text-slate-800 text-sm mb-1">
              {refFile ? refFile.name : 'Upload Baseline / Reference CSV'}
            </h4>
            <p className="text-xs text-slate-400">Drag & drop or browse training/benchmark data</p>
          </div>
        </div>

        {/* Current Upload */}
        <div className="bg-white p-6 rounded-2xl border-2 border-dashed border-slate-200 hover:border-orange-400 transition-all text-center relative group">
          <input
            type="file"
            accept=".csv"
            onChange={handleCurUpload}
            className="absolute inset-0 opacity-0 cursor-pointer w-full h-full z-10"
          />
          <div className="flex flex-col items-center justify-center pointer-events-none">
            <div className="p-3 bg-orange-50 text-orange-600 rounded-xl mb-3 group-hover:scale-110 transition-transform">
              <UploadCloud size={24} />
            </div>
            <h4 className="font-bold text-slate-800 text-sm mb-1">
              {curFile ? curFile.name : 'Upload Current Production CSV'}
            </h4>
            <p className="text-xs text-slate-400">Drag & drop or browse live production inference logs</p>
          </div>
        </div>
      </div>

      {/* Dataset Previews */}
      {(refPreview.length > 0 || curPreview.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          {refPreview.length > 0 && (
            <div>
              <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <FileSpreadsheet size={14} className="text-blue-600" /> Reference Preview (First 3 Rows)
              </h5>
              <div className="overflow-x-auto border border-slate-100 rounded-xl">
                <table className="min-w-full text-xs text-left">
                  <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-100">
                    <tr>
                      {refColumns.map((c) => (
                        <th key={c} className="px-3 py-2 whitespace-nowrap">{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {refPreview.map((r, i) => (
                      <tr key={i}>
                        {refColumns.map((c) => (
                          <td key={c} className="px-3 py-1.5 whitespace-nowrap text-slate-600">{r[c]}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {curPreview.length > 0 && (
            <div>
              <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <FileSpreadsheet size={14} className="text-orange-600" /> Current Preview (First 3 Rows)
              </h5>
              <div className="overflow-x-auto border border-slate-100 rounded-xl">
                <table className="min-w-full text-xs text-left">
                  <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-100">
                    <tr>
                      {curColumns.map((c) => (
                        <th key={c} className="px-3 py-2 whitespace-nowrap">{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {curPreview.map((r, i) => (
                      <tr key={i}>
                        {curColumns.map((c) => (
                          <td key={c} className="px-3 py-1.5 whitespace-nowrap text-slate-600">{r[c]}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Action: Run Drift Report Button */}
      {refFile && curFile && (
        <div className="flex justify-center pt-2">
          <button
            onClick={handleRunDrift}
            disabled={loadingDrift}
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm shadow-md transition-all cursor-pointer disabled:opacity-50"
          >
            <Play size={16} fill="white" />
            {loadingDrift ? 'Computing PSI, KS, JS, Wasserstein & Evidently...' : 'Run Batch Drift Report'}
          </button>
        </div>
      )}

      {/* Drift Detection Results View */}
      {driftReport && (
        <div className="space-y-6 pt-4">
          {/* KPI Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider block mb-1">
                Overall Dataset Drift
              </span>
              <div className="flex items-center gap-2">
                {driftReport.evidently_overall?.drift_detected ? (
                  <>
                    <AlertCircle size={20} className="text-red-500" />
                    <span className="text-xl font-extrabold text-red-600">DETECTED</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={20} className="text-emerald-500" />
                    <span className="text-xl font-extrabold text-emerald-600">STABLE</span>
                  </>
                )}
              </div>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider block mb-1">
                Share of Drifted Columns
              </span>
              <div className="text-2xl font-black text-slate-900">
                {(shareDrift * 100).toFixed(1)}%
              </div>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider block mb-1">
                Drifted Features
              </span>
              <div className="text-2xl font-black text-slate-900">
                {driftedCount} / {featureNames.length}
              </div>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider block mb-1">
                Max PSI Score
              </span>
              <div className="text-2xl font-black text-slate-900">
                {Math.max(...featureNames.map((c) => stats[c]?.PSI?.value || 0)).toFixed(4)}
              </div>
            </div>
          </div>

          {/* Visual Charts Overview */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Pie Share */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <PieIcon size={14} className="text-blue-600" /> Evidently Feature Drift Share
              </h4>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} dataKey="value" innerRadius={45} outerRadius={65} paddingAngle={4}>
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex justify-center gap-4 text-xs font-semibold text-slate-600">
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-red-500" /> Drifted ({driftedCount})</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Stable ({stableCount})</span>
              </div>
            </div>

            {/* PSI Bar Chart */}
            <div className="lg:col-span-2 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <BarChart2 size={14} className="text-blue-600" /> Population Stability Index (PSI) per Feature
              </h4>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={psiChartData} margin={{ top: 10, right: 10, bottom: 25, left: -10 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="feature" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <ReferenceLine y={0.10} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: 'Moderate (0.10)', fill: '#f59e0b', fontSize: 10 }} />
                    <ReferenceLine y={0.25} stroke="#ef4444" strokeDasharray="3 3" label={{ value: 'Major (0.25)', fill: '#ef4444', fontSize: 10 }} />
                    <Bar dataKey="PSI" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Column-Level Statistical Metrics Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-slate-100 bg-slate-50/50">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Column-Level Multi-Test Statistical Matrix
              </h4>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Feature</th>
                    <th className="px-4 py-3">PSI Value</th>
                    <th className="px-4 py-3">PSI Drift</th>
                    <th className="px-4 py-3">KS p-value</th>
                    <th className="px-4 py-3">KS Drift</th>
                    <th className="px-4 py-3">JS Divergence</th>
                    <th className="px-4 py-3">Wasserstein Dist</th>
                    <th className="px-4 py-3 text-right">Verdict</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {featureNames.map((col) => {
                    const m = stats[col]
                    const anyDrift =
                      m.PSI?.drift_detected ||
                      m.KS_Test?.drift_detected ||
                      m.JS_Divergence?.drift_detected ||
                      m.Wasserstein?.drift_detected

                    return (
                      <tr key={col} className="hover:bg-slate-50/60 transition-colors">
                        <td className="px-4 py-3 font-semibold text-slate-900">{col}</td>
                        <td className="px-4 py-3 font-mono">{m.PSI?.value?.toFixed(4)}</td>
                        <td className="px-4 py-3">
                          {m.PSI?.drift_detected ? (
                            <span className="text-red-600 font-bold">YES</span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 font-mono">{m.KS_Test?.p_value?.toExponential(2)}</td>
                        <td className="px-4 py-3">
                          {m.KS_Test?.drift_detected ? (
                            <span className="text-red-600 font-bold">YES</span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 font-mono">{m.JS_Divergence?.divergence?.toFixed(4)}</td>
                        <td className="px-4 py-3 font-mono">{m.Wasserstein?.normalized_distance?.toFixed(4)}</td>
                        <td className="px-4 py-3 text-right">
                          <span
                            className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold ${
                              anyDrift ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'
                            }`}
                          >
                            {anyDrift ? 'DRIFTED' : 'STABLE'}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* RCA Trigger Section */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-2xl p-6 text-center space-y-3">
            <h4 className="text-base font-bold text-slate-900">Drift Detected? Discover WHY with Root Cause Analysis</h4>
            <p className="text-xs text-slate-600 max-w-xl mx-auto">
              Execute deterministic causal isolation: location shifts, scale modifications, variance transformations,
              new category anomalies, and missing value injections.
            </p>
            <button
              onClick={handleRunRca}
              disabled={loadingRca}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm shadow-md transition-all cursor-pointer disabled:opacity-50"
            >
              <Search size={16} />
              {loadingRca ? 'Executing Root Cause Analysis Engine...' : 'Run Root Cause Analysis (RCA)'}
            </button>
          </div>

          {/* RCA Results Output */}
          {rcaIncident && (
            <RcaReportView
              incident={rcaIncident}
              refData={refRawData}
              curData={curRawData}
              onDownloadPdf={() => downloadFile('/api/rca/pdf', 'rca_report.pdf', 'application/pdf')}
              onDownloadMd={() => downloadFile('/api/rca/markdown', 'rca_report.md', 'text/markdown')}
              onDownloadJson={() => {
                const blob = new Blob([JSON.stringify(rcaIncident, null, 2)], { type: 'application/json' })
                const url = URL.createObjectURL(blob)
                const link = document.createElement('a')
                link.href = url
                link.download = 'rca_report.json'
                link.click()
              }}
            />
          )}
        </div>
      )}
    </div>
  )
}
