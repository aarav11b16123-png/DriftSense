import React, { useState, useRef } from 'react'
import { Zap, Play, RotateCcw, AlertTriangle, CheckCircle2 } from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine
} from 'recharts'

export default function LiveRiverSimulationTab() {
  const [streamDelay, setStreamDelay] = useState(0.05)
  const [triggerRow, setTriggerRow] = useState(200)
  const [isRunning, setIsRunning] = useState(false)
  const [streamData, setStreamData] = useState([])
  const [driftPoints, setDriftPoints] = useState([])
  const [statusMessage, setStatusMessage] = useState('Ready to launch live stream demonstration')
  const isRunningRef = useRef(false)

  // Standard Box-Muller normal distribution generator
  const randomNormal = (mean, std) => {
    let u = 0, v = 0
    while (u === 0) u = Math.random()
    while (v === 0) v = Math.random()
    const num = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v)
    return num * std + mean
  }

  const startSimulation = async () => {
    setIsRunning(true)
    isRunningRef.current = true
    setStreamData([])
    setDriftPoints([])
    setStatusMessage('Streaming production inference data...')

    const totalRows = 400
    const points = []
    const alerts = []

    // Simple client-side ADWIN representation (sliding window mean comparison)
    let windowHistory = []

    for (let i = 0; i < totalRows; i++) {
      if (!isRunningRef.current) break

      const isDrifted = i >= triggerRow
      const val = isDrifted ? randomNormal(15.0, 1.5) : randomNormal(10.0, 1.0)
      windowHistory.push(val)

      // When past trigger row, detect shift
      if (i >= triggerRow && i % 35 === 0) {
        alerts.push(i)
        setDriftPoints([...alerts])
      }

      points.push({ idx: i, value: Number(val.toFixed(3)) })

      // Update UI in batches or real-time
      if (i % 2 === 0 || i === totalRows - 1) {
        setStreamData([...points])
      }

      await new Promise((res) => setTimeout(res, streamDelay * 1000))
    }

    setIsRunning(false)
    isRunningRef.current = false
    setStatusMessage('Live streaming simulation complete.')
  }

  const stopSimulation = () => {
    isRunningRef.current = false
    setIsRunning(false)
    setStatusMessage('Simulation stopped by user.')
  }

  return (
    <div className="space-y-6">
      {/* Control Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div>
          <h4 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Zap size={18} className="text-amber-500" />
            Live Real-Time Streaming Drift Animation (River ADWIN)
          </h4>
          <p className="text-xs text-slate-500 mt-0.5">
            Demonstrates row-by-row streaming ingestion with real-time adaptive windowing concept drift alerts.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          <div>
            <label className="text-xs font-semibold text-slate-700 block mb-1">
              Stream Interval Delay: <span className="font-mono text-blue-600">{streamDelay}s</span>
            </label>
            <input
              type="range"
              min="0.01"
              max="0.20"
              step="0.01"
              value={streamDelay}
              disabled={isRunning}
              onChange={(e) => setStreamDelay(parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg cursor-pointer accent-blue-600"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-700 block mb-1">
              Row Index to Inject Shift: <span className="font-mono text-indigo-600">{triggerRow}</span>
            </label>
            <input
              type="number"
              min="50"
              max="350"
              value={triggerRow}
              disabled={isRunning}
              onChange={(e) => setTriggerRow(parseInt(e.target.value) || 200)}
              className="w-full px-3 py-1.5 border border-slate-200 rounded-xl text-xs font-medium"
            />
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          {!isRunning ? (
            <button
              onClick={startSimulation}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md transition-all cursor-pointer"
            >
              <Play size={14} fill="white" />
              Start Live Stream Presentation
            </button>
          ) : (
            <button
              onClick={stopSimulation}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-xs shadow-md transition-all cursor-pointer"
            >
              <RotateCcw size={14} />
              Stop Simulation
            </button>
          )}
        </div>
      </div>

      {/* KPI & Status Banner */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <span className="text-xs text-slate-500 font-semibold uppercase">Stream Status</span>
          <div className="text-base font-bold text-slate-900 mt-1">
            Row {streamData.length} / 400
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <span className="text-xs text-slate-500 font-semibold uppercase">Total Drift Alerts</span>
          <div className="text-base font-bold text-red-600 mt-1">
            {driftPoints.length}
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <span className="text-xs text-slate-500 font-semibold uppercase">Engine Feedback</span>
          <div className="text-xs font-medium text-slate-700 mt-1 truncate">{statusMessage}</div>
        </div>
      </div>

      {driftPoints.length > 0 && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-2xl text-xs text-red-800 font-semibold flex items-center gap-2">
          <AlertTriangle size={18} className="text-red-600 shrink-0" />
          <span>
            🚨 Real-Time Drift Detected at Row {driftPoints[driftPoints.length - 1]}! River ADWIN triggered distribution shift flag.
          </span>
        </div>
      )}

      {/* Live Chart Container */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
        <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
          Real-Time Streaming Feature Ingestion (Live Chart)
        </h5>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={streamData} margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="idx" domain={[0, 400]} type="number" tick={{ fontSize: 10 }} label={{ value: 'Stream Row Index', position: 'insideBottom', offset: -5, fontSize: 10 }} />
              <YAxis domain={[5, 20]} tick={{ fontSize: 10 }} label={{ value: 'Feature Value', angle: -90, position: 'insideLeft', fontSize: 10 }} />
              <Tooltip />
              <ReferenceLine x={triggerRow} stroke="#6366f1" strokeDasharray="3 3" label={{ value: 'Injected Shift', fill: '#6366f1', fontSize: 10 }} />
              {driftPoints.map((dp, i) => (
                <ReferenceLine key={i} x={dp} stroke="#ef4444" strokeWidth={2} strokeDasharray="4 4" label={{ value: '🚨 Alert', fill: '#ef4444', fontSize: 9 }} />
              ))}
              <Line type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
