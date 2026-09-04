import { BrainCircuit, ShieldAlert } from 'lucide-react'
import type { AlertItem, GraphNode } from '../types'

interface Props {
  nodes: GraphNode[]
  alerts: AlertItem[]
  onSelect: (node: GraphNode) => void
}

export function RiskPanel({ nodes, alerts, onSelect }: Props) {
  const top = [...nodes].sort((a, b) => b.risk - a.risk).slice(0, 4)
  const reviewSignals = nodes.filter((node) => node.risk >= 85)
  const averageRisk = nodes.length ? Math.round(nodes.reduce((total, node) => total + node.risk, 0) / nodes.length) : 0
  const reviewShare = nodes.length ? Math.round(reviewSignals.length / nodes.length * 100) : 0
  return (
    <section className="panel risk-panel">
      <div className="panel-header"><div><span className="eyebrow">THREAT ASSESSMENT</span><h2>Risk signals</h2></div><span className="risk-status"><i /> ELEVATED</span></div>
      <div className="overall-risk">
        <div className="risk-gauge"><svg viewBox="0 0 120 68"><path d="M14 61a46 46 0 0 1 92 0" pathLength="100"/><path className="risk-fill" d="M14 61a46 46 0 0 1 92 0" pathLength="100" style={{strokeDasharray:`${averageRisk} 100`}}/></svg><strong>{averageRisk}</strong><small>/ 100</small></div>
        <div><strong>{reviewSignals.length}</strong><span>Review signals</span><small>{reviewShare}% of graph entities</small></div>
      </div>
      <div className="mini-heading"><span>HIGH-RISK ENTITIES</span><em>TOP {top.length}</em></div>
      <div className="risk-entities">
        {top.map((node, index) => <button key={node.id} onClick={() => onSelect(node)}><span className={`rank rank-${index + 1}`}>{String(index + 1).padStart(2, '0')}</span><span className={`entity-dot ${node.type}`} /><span><strong>{node.name}</strong><small>{node.type}</small></span><em>{node.risk}</em></button>)}
      </div>
      <div className="mini-heading"><span>ACTIVE ANOMALIES</span><em>{alerts.filter((alert) => !alert.acknowledged).length} OPEN</em></div>
      {alerts[0] && <div className="anomaly-summary">
        <span><ShieldAlert size={17} /></span><div><strong>{alerts[0].title}</strong><p>{alerts[0].detail}</p><small><BrainCircuit size={11} /> Signal confidence {alerts[0].confidence}%</small></div>
      </div>}
    </section>
  )
}
