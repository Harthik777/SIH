import type { LucideIcon } from 'lucide-react'

interface Props {
  icon: LucideIcon
  label: string
  value: string
  delta: string
  tone?: 'mint' | 'amber' | 'violet' | 'red'
  chart?: number[]
}

export function StatCard({ icon: Icon, label, value, delta, tone = 'mint', chart = [2, 4, 3, 6, 5, 8, 7] }: Props) {
  const max = Math.max(...chart)
  const points = chart.map((point, index) => `${(index / (chart.length - 1)) * 100},${28 - (point / max) * 23}`).join(' ')
  return (
    <article className={`stat-card ${tone}`}>
      <div className="stat-head"><span><Icon size={17} /></span><small>{label}</small></div>
      <div className="stat-body"><strong>{value}</strong><em>{delta}</em></div>
      <svg viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true">
        <defs><linearGradient id={`fill-${tone}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="currentColor" stopOpacity=".25"/><stop offset="1" stopColor="currentColor" stopOpacity="0"/></linearGradient></defs>
        <polygon points={`0,30 ${points} 100,30`} fill={`url(#fill-${tone})`} />
        <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.7" vectorEffect="non-scaling-stroke" />
      </svg>
    </article>
  )
}

