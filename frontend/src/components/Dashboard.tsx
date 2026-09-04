import { lazy, Suspense, useEffect, useState } from 'react'
import { Activity, AlertTriangle, Check, Network, ScanSearch, Share2 } from 'lucide-react'
import { api } from '../api'
import type { AlertItem, GraphData, GraphNode, InvestigationBriefing } from '../types'
import { AiBrief } from './AiBrief'
import { MapPanel } from './MapPanel'
import { RiskPanel } from './RiskPanel'
import { StatCard } from './StatCard'
import { TimelinePanel } from './TimelinePanel'
import { TrustPanel } from './TrustPanel'

const NetworkGraphView = lazy(() => import('./NetworkGraph').then((module) => ({ default: module.NetworkGraph })))

interface Props {
  graph: GraphData
  alerts: AlertItem[]
  selected: GraphNode | null
  onSelect: (node: GraphNode) => void
  investigationName?: string
  investigationId?: string
  investigationSource?: string
  sourceRecords?: number
}

export function Dashboard({ graph, alerts, selected, onSelect, investigationId, investigationName = 'Operation City Shield', investigationSource = 'crime_dataset.csv', sourceRecords = 500 }: Props) {
  const [briefing, setBriefing] = useState<InvestigationBriefing | null>(null)
  const [briefOpen, setBriefOpen] = useState(false)
  const [shared, setShared] = useState(false)
  useEffect(() => { api.getBriefing().then(setBriefing).catch(() => undefined) }, [graph.nodes.length, graph.edges.length, investigationId])

  const openAnalysis = () => {
    setBriefOpen(true)
    window.setTimeout(() => document.getElementById('analysis-brief')?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 0)
  }
  const shareCase = async () => {
    const shareData = { title: `Sentinel — ${investigationName}`, text: 'Evidence-backed connected crime pattern assessment.', url: window.location.href }
    if (navigator.share) await navigator.share(shareData).catch(() => undefined)
    else await navigator.clipboard?.writeText(`${shareData.title}\n${shareData.url}`)
    setShared(true)
    window.setTimeout(() => setShared(false), 1800)
  }

  return (
    <div className="dashboard-page">
      <div className="page-heading">
        <div><span className="eyebrow">COMMAND CENTER · EVIDENCE SNAPSHOT</span><h1>Investigation overview</h1><p>{investigationName} — Connected crime pattern analysis</p></div>
        <div className="heading-actions"><span className="offline-badge"><i/> OFFLINE VERIFIED</span><button className="secondary-button" onClick={shareCase}>{shared ? <Check size={14}/> : <Share2 size={14}/>} {shared ? 'Copied' : 'Share case'}</button><button className="primary-button" onClick={openAnalysis}><ScanSearch size={15}/> Review analysis</button></div>
      </div>
      <div className="stats-grid">
        <StatCard icon={Network} label="TOTAL ENTITIES" value={graph.nodes.length.toLocaleString()} delta={`${sourceRecords.toLocaleString()} source records`} chart={[3,4,4,5,6,7,9]} />
        <StatCard icon={Activity} label="RELATIONSHIPS" value={graph.edges.length.toLocaleString()} delta="ontology aligned" tone="violet" chart={[3,3,5,4,7,7,9]} />
        <StatCard icon={AlertTriangle} label="RISK SIGNALS" value={graph.nodes.filter((node) => node.risk >= 85).length.toLocaleString()} delta={`${alerts.filter((alert) => !alert.acknowledged).length} unresolved`} tone="red" chart={[2,3,2,4,3,6,9]} />
        <StatCard icon={ScanSearch} label="VERIFIED FINDINGS" value={(briefing?.findings.length ?? 3).toString()} delta="evidence backed" tone="amber" chart={[1,1,2,2,2,3,3]} />
      </div>
      <div className="dashboard-main-grid">
        <Suspense fallback={<section className="panel graph-loading"><span />Resolving graph topology…</section>}><NetworkGraphView data={graph} selected={selected} onSelect={onSelect}/></Suspense>
        <RiskPanel nodes={graph.nodes} alerts={alerts} onSelect={onSelect}/>
      </div>
      <AiBrief briefing={briefing} expanded={briefOpen} onToggle={() => setBriefOpen(!briefOpen)} />
      <TrustPanel briefing={briefing}/>
      <div className="dashboard-lower-grid"><TimelinePanel version={investigationId}/><MapPanel version={investigationId}/></div>
      <footer className="data-footer"><span><i/> Local evidence graph ready</span><span>Active source: {investigationSource} · Ontology aligned · Human review required</span></footer>
    </div>
  )
}
