import { useState } from 'react'
import { AlertTriangle, Check, CheckCircle2, ChevronRight, Clock, Download, Filter, Search, ShieldAlert } from 'lucide-react'
import { api } from '../api'
import type { AlertItem, GraphNode, Severity } from '../types'

interface Props {
  initialAlerts: AlertItem[]
  nodes: GraphNode[]
  onAlertsChange: (alerts: AlertItem[]) => void
  onAcknowledge: (id: string) => Promise<void>
  onSelectNode: (node: GraphNode) => void
}

const severityOrder: Record<Severity, number> = { critical: 4, high: 3, medium: 2, low: 1 }

export function AlertsPage({ initialAlerts, nodes, onAlertsChange, onAcknowledge, onSelectNode }: Props) {
  const [filter, setFilter] = useState<'all'|'open'|'acknowledged'>('all')
  const [query, setQuery] = useState('')
  const visible = initialAlerts.filter((alert) => (filter === 'all' || (filter === 'open' ? !alert.acknowledged : alert.acknowledged)) && `${alert.title} ${alert.detail}`.toLowerCase().includes(query.toLowerCase())).sort((a,b) => severityOrder[b.severity]-severityOrder[a.severity])
  const acknowledge = async (id: string) => {
    await onAcknowledge(id)
    onAlertsChange(initialAlerts.map((alert) => alert.id === id ? { ...alert, acknowledged: true } : alert))
  }
  const averageConfidence = initialAlerts.length ? Math.round(initialAlerts.reduce((sum, alert) => sum + alert.confidence, 0) / initialAlerts.length) : 0
  const linkedEntities = new Set(initialAlerts.map((alert) => alert.entityId)).size
  return (
    <div className="standard-page">
      <div className="page-heading"><div><span className="eyebrow">ACTIVE-DATASET MONITORING</span><h1>Alert center</h1><p>Triage deterministic risk signals with human verification.</p></div><button className="secondary-button" onClick={()=>void api.download('/api/export/data/csv?dataset=alerts','sentinel_alerts.csv')}><Download size={14}/> Export alert log</button></div>
      <div className="alert-summary-grid">
        <div className="critical"><ShieldAlert size={20}/><span><strong>{initialAlerts.filter(a=>a.severity==='critical').length}</strong><small>Critical</small></span><em>Immediate review</em></div>
        <div className="high"><AlertTriangle size={20}/><span><strong>{initialAlerts.filter(a=>a.severity==='high').length}</strong><small>High priority</small></span><em>&lt; 4 hour SLA</em></div>
        <div><Clock size={20}/><span><strong>{initialAlerts.filter(a=>!a.acknowledged).length}</strong><small>Unresolved</small></span><em>Across {linkedEntities} linked entities</em></div>
        <div><CheckCircle2 size={20}/><span><strong>{averageConfidence}%</strong><small>Avg. confidence</small></span><em>Source-derived rules</em></div>
      </div>
      <section className="panel alerts-table-panel">
        <div className="alert-toolbar">
          <div className="segmented">{(['all','open','acknowledged'] as const).map(item=><button key={item} className={filter===item?'active':''} onClick={()=>setFilter(item)}>{item}<em>{item==='all'?initialAlerts.length:item==='open'?initialAlerts.filter(a=>!a.acknowledged).length:initialAlerts.filter(a=>a.acknowledged).length}</em></button>)}</div>
          <div className="toolbar-search"><Search size={14}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search alerts…"/></div><span className="filter-button"><Filter size={14}/> {visible.length} shown</span>
        </div>
        <div className="alert-list">
          {visible.map(alert=>{
            const node=nodes.find(item=>item.id===alert.entityId)
            return <article key={alert.id} className={alert.acknowledged?'acknowledged':''}><span className={`severity-mark ${alert.severity}`}><AlertTriangle size={17}/></span><div className="alert-main"><div><span className={`severity-label ${alert.severity}`}>{alert.severity}</span><small>{alert.time}</small></div><h3>{alert.title}</h3><p>{alert.detail}</p><button onClick={()=>node&&onSelectNode(node)} disabled={!node}>Related entity: <strong>{node?.name ?? 'not resolved'}</strong><ChevronRight size={12}/></button></div><div className="alert-confidence"><small>SIGNAL CONFIDENCE</small><strong>{alert.confidence}%</strong><div><i style={{width:`${alert.confidence}%`}}/></div></div><div className="alert-actions">{alert.acknowledged?<span><Check size={13}/> Acknowledged</span>:<button onClick={()=>void acknowledge(alert.id)}><Check size={13}/> Acknowledge</button>}</div></article>})}
        </div>
      </section>
    </div>
  )
}
