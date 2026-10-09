import React, { useState } from 'react'
import axios from 'axios'
import { Server, Download, RefreshCw, UploadCloud, AlertTriangle, Play } from 'lucide-react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import RcaReportView from './RcaReportView'

export default function ApiIntegrationTab() {
  const [subTab, setSubTab] = useState('2a')

  // 2A State
  const [apiBatchData, setApiBatchData] = useState([])
  const [loadingFetchBatch, setLoadingFetchBatch] = useState(false)
  const [refFileApi, setRefFileApi] = useState(null)
  const [refRawData, setRefRawData] = useState({})
  const [apiReport, setApiReport] = useState(null)
  const [loadingApiDrift, setLoadingApiDrift] = useState(false)
  const [apiIncident, setApiIncident] = useState(null)
  const [loadingApiRca, setLoadingApiRca] = useState(false)

  // 2B State
  const [streamRecords, setStreamRecords] = useState([])
  const [streamAlerts, setStreamAlerts] = useState([])
  const [loadingStream, setLoadingStream] = useState(false)

  const handleFetchBatch = async () => {
    setLoadingFetchBatch(true)
    try {
      const res = await axios.get('http://localhost:8000/api/v1/get-batch-data')
      const data = res.data?.data || []
      setApiBatchData(data)
      if (data.length === 0) {
        alert('No batch logs found on API server. Please post to http://localhost:8000/api/v1/log-batch first.')
      }
    } catch (err) {
      alert('Could not connect to FastAPI server at http://localhost:8000: ' + err.message)
    } finally {
      setLoadingFetchBatch(false)
    }
  }

  const handleRefUploadApi = (e) => {
    const file = e.target.files[0]
    if (file) {
      setRefFileApi(file)
      const reader = new FileReader()
      reader.onload = (ev) => {
        const text = ev.target.result
        const lines = text.split(/\r\n|\n/).filter((l) => l.trim() !== '')
        if (lines.length > 0) {
          const headers = lines[0].split(',').map((h) => h.trim().replace(/^"|"$/g, ''))
          const colMap = {}
          headers.forEach((h) => (colMap[h] = []))
          lines.slice(1, 1001).forEach((line) => {
            const vals = line.split(',')
            headers.forEach((h, i) => {
              const num = parseFloat(vals[i])
              if (!isNaN(num)) colMap[h].push(num)
            })
          })
          setRefRawData(colMap)
        }
      }
      reader.readAsText(file)
    }
  }

  const handleRunApiDrift = async () => {
    if (!refFileApi || !apiBatchData.length) return
    setLoadingApiDrift(true)

    // Convert apiBatchData to CSV Blob
    const headers = Object.keys(apiBatchData[0]).join(',')
    const rows = apiBatchData.map((obj) => Object.values(obj).join(','))
    const curCsvBlob = new Blob([[headers, ...rows].join('\n')], { type: 'text/csv' })

    const formData = new FormData()
    formData.append('reference', refFileApi)
    formData.append('current', curCsvBlob, 'api_current.csv')

    try {
      const res = await axios.post('/api/drift', formData)
      setApiReport(res.data)
    } catch (err) {
      alert('Error analyzing API drift: ' + err.message)
    } finally {
      setLoadingApiDrift(false)
    }
  }

  const handleRunApiRca = async () => {
    if (!refFileApi || !apiBatchData.length) return
    setLoadingApiRca(true)

    const headers = Object.keys(apiBatchData[0]).join(',')
    const rows = apiBatchData.map((obj) => Object.values(obj).join(','))
    const curCsvBlob = new Blob([[headers, ...rows].join('\n')], { type: 'text/csv' })

    const formData = new FormData()
    formData.append('reference', refFileApi)
    formData.append('current', curCsvBlob, 'api_current.csv')

    try {
      const res = await axios.post('/api/rca', formData)
      setApiIncident(res.data)
    } catch (err) {
      alert('Error analyzing API RCA: ' + err.message)
    } finally {
      setLoadingApiRca(false)
    }
  }

  const handlePollStream = async () => {
    setLoadingStream(true)
    try {
      const res = await axios.get('http://localhost:8000/api/v1/get-stream-data')
      const buffer = res.data?.stream || []
      const features = buffer.map((b, idx) => ({ idx, ...b.features }))
      const alerts = buffer
        .map((b, idx) => ({ idx, alerts: b.drift_alerts }))
        .filter((b) => Object.keys(b.alerts || {}).length > 0)

      setStreamRecords(features)
      setStreamAlerts(alerts)
    } catch (err) {
      alert('Could not connect to FastAPI stream buffer: ' + err.message)
    } finally {
      setLoadingStream(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Sub-tab selection */}
      <div className="flex gap-2 border-b border-slate-200 pb-3">
        <button
          onClick={() => setSubTab('2a')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            subTab === '2a' ? 'bg-slate-900 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          2A. API Batch Data Ingestion
        </button>
        <button
          onClick={() => setSubTab('2b')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            subTab === '2b' ? 'bg-slate-900 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          2B. API Live Stream Listener
        </button>
      </div>

      {/* 2A. API Batch */}
      {subTab === '2a' && (
        <div className="space-y-5">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h4 className="font-bold text-slate-900 text-sm">Batch Ingestion Endpoint</h4>
                <code className="text-xs bg-slate-100 text-blue-600 px-2 py-1 rounded-md font-mono mt-1 inline-block">
                  POST http://localhost:8000/api/v1/log-batch
                </code>
              </div>
              <button
                onClick={handleFetchBatch}
                disabled={loadingFetchBatch}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm transition-all cursor-pointer disabled:opacity-50"
              >
                <RefreshCw size={14} className={loadingFetchBatch ? 'animate-spin' : ''} />
                Fetch Ingested Logs from API
              </button>
            </div>

            {apiBatchData.length > 0 && (
              <div className="pt-3 border-t border-slate-100 space-y-3">
                <span className="text-xs font-semibold text-emerald-600">
                  ✓ Fetched {apiBatchData.length} records from production API memory.
                </span>
                <div className="max-h-40 overflow-auto border border-slate-100 rounded-xl">
                  <table className="min-w-full text-xs text-left">
                    <thead className="bg-slate-50 text-slate-500 font-semibold sticky top-0">
                      <tr>
                        {Object.keys(apiBatchData[0]).map((h) => (
                          <th key={h} className="px-3 py-2 whitespace-nowrap">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {apiBatchData.slice(0, 5).map((row, i) => (
                        <tr key={i}>
                          {Object.values(row).map((v, vi) => (
                            <td key={vi} className="px-3 py-1.5 whitespace-nowrap text-slate-600">{String(v)}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {/* Reference CSV Upload for Comparison */}
          {apiBatchData.length > 0 && (
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <h4 className="font-bold text-slate-900 text-sm">Upload Baseline Reference CSV</h4>
              <div className="p-4 border-2 border-dashed border-slate-200 rounded-xl text-center relative group hover:border-blue-400">
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleRefUploadApi}
                  className="absolute inset-0 opacity-0 cursor-pointer w-full h-full z-10"
                />
                <div className="flex flex-col items-center">
                  <UploadCloud size={20} className="text-blue-500 mb-1" />
                  <span className="text-xs font-bold text-slate-700">
                    {refFileApi ? refFileApi.name : 'Select Baseline Reference CSV'}
                  </span>
                </div>
              </div>

              {refFileApi && (
                <div className="flex gap-3">
                  <button
                    onClick={handleRunApiDrift}
                    disabled={loadingApiDrift}
                    className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm transition-all cursor-pointer"
                  >
                    <Play size={14} fill="white" />
                    {loadingApiDrift ? 'Computing...' : 'Run Drift on API Logs'}
                  </button>

                  {apiReport && (
                    <button
                      onClick={handleRunApiRca}
                      disabled={loadingApiRca}
                      className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-sm transition-all cursor-pointer"
                    >
                      <Server size={14} />
                      {loadingApiRca ? 'Analyzing...' : 'Run RCA on API Logs'}
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* API RCA Output */}
          {apiIncident && (
            <RcaReportView
              incident={apiIncident}
              refData={refRawData}
              curData={apiBatchData.reduce((acc, row) => {
                Object.keys(row).forEach((k) => {
                  if (!acc[k]) acc[k] = []
                  acc[k].push(row[k])
                })
                return acc
              }, {})}
            />
          )}
        </div>
      )}

      {/* 2B. API Stream */}
      {subTab === '2b' && (
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h4 className="font-bold text-slate-900 text-sm">Real-Time Streaming Listener</h4>
              <code className="text-xs bg-slate-100 text-indigo-600 px-2 py-1 rounded-md font-mono mt-1 inline-block">
                POST http://localhost:8000/api/v1/log-stream
              </code>
            </div>
            <button
              onClick={handlePollStream}
              disabled={loadingStream}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold shadow-sm transition-all cursor-pointer"
            >
              <RefreshCw size={14} className={loadingStream ? 'animate-spin' : ''} />
              Poll Live Stream Buffer
            </button>
          </div>

          {streamRecords.length > 0 ? (
            <div className="space-y-4 pt-2">
              <span className="text-xs text-slate-500 font-medium">
                Retrieved {streamRecords.length} live stream events.
              </span>

              {streamAlerts.length > 0 && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 font-medium flex items-center gap-2">
                  <AlertTriangle size={16} className="text-red-600 shrink-0" />
                  <span>River ADWIN detected real-time drift alerts at stream indices: {streamAlerts.map((a) => a.idx).join(', ')}</span>
                </div>
              )}

              <div className="h-64 border border-slate-100 rounded-xl p-3 bg-slate-50/50">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={streamRecords} margin={{ top: 10, right: 10, bottom: 10, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="idx" tick={{ fontSize: 10 }} label={{ value: 'Stream Index', position: 'insideBottom', offset: -5, fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip />
                    {Object.keys(streamRecords[0])
                      .filter((k) => k !== 'idx')
                      .map((k, i) => (
                        <Line key={k} type="monotone" dataKey={k} stroke={['#2563eb', '#f97316', '#10b981', '#8b5cf6'][i % 4]} dot={false} strokeWidth={2} />
                      ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-400 text-center py-8">
              Stream buffer is empty. Post events to <code>/api/v1/log-stream</code> to observe live drift alerts.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
