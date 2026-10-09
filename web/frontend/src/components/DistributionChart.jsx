import React from 'react'
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid
} from 'recharts'

export default function DistributionChart({ featureName, refData = [], curData = [] }) {
  if (!refData.length || !curData.length) {
    return (
      <div className="h-48 flex items-center justify-center text-slate-400 text-sm bg-slate-50 rounded-xl">
        No distribution data available
      </div>
    )
  }

  // Calculate 10 histogram bins
  const cleanRef = refData.filter((v) => typeof v === 'number' && !isNaN(v))
  const cleanCur = curData.filter((v) => typeof v === 'number' && !isNaN(v))

  if (!cleanRef.length || !cleanCur.length) {
    return null
  }

  const min = Math.min(...cleanRef, ...cleanCur)
  const max = Math.max(...cleanRef, ...cleanCur)
  const numBins = 10
  const step = (max - min) / (numBins || 1)

  const bins = Array.from({ length: numBins }, (_, i) => {
    const start = min + i * step
    const end = start + step
    return {
      range: `${start.toFixed(1)} - ${end.toFixed(1)}`,
      mid: Number(((start + end) / 2).toFixed(2)),
      refCount: 0,
      curCount: 0,
    }
  })

  cleanRef.forEach((v) => {
    let idx = Math.floor((v - min) / (step || 1))
    if (idx >= numBins) idx = numBins - 1
    if (idx < 0) idx = 0
    bins[idx].refCount++
  })

  cleanCur.forEach((v) => {
    let idx = Math.floor((v - min) / (step || 1))
    if (idx >= numBins) idx = numBins - 1
    if (idx < 0) idx = 0
    bins[idx].curCount++
  })

  const chartData = bins.map((b) => {
    const refProb = b.refCount / cleanRef.length
    const curProb = b.curCount / cleanCur.length
    const p = Math.max(refProb, 1e-4)
    const q = Math.max(curProb, 1e-4)
    const psiContrib = (q - p) * Math.log(q / p)

    return {
      bin: b.range,
      Reference: Number((refProb * 100).toFixed(2)),
      Current: Number((curProb * 100).toFixed(2)),
      'PSI Contrib': Number((psiContrib * 100).toFixed(2)),
    }
  })

  return (
    <div className="bg-white p-4 rounded-xl border border-slate-100">
      <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-3">
        Distribution Comparison & PSI Contribution: {featureName}
      </h4>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 10, right: 20, bottom: 25, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="bin" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" />
            <YAxis yAxisId="left" tick={{ fontSize: 11 }} label={{ value: '% Density', angle: -90, position: 'insideLeft', fontSize: 11 }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} label={{ value: 'PSI %', angle: 90, position: 'insideRight', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#ffffff', borderRadius: '12px', borderColor: '#e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            />
            <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '12px' }} />
            <Bar yAxisId="left" dataKey="Reference" fill="#3b82f6" fillOpacity={0.7} radius={[4, 4, 0, 0]} />
            <Bar yAxisId="left" dataKey="Current" fill="#f97316" fillOpacity={0.7} radius={[4, 4, 0, 0]} />
            <Bar yAxisId="right" dataKey="PSI Contrib" fill="#ef4444" fillOpacity={0.6} radius={[4, 4, 0, 0]} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
