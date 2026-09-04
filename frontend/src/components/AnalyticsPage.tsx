import { useEffect, useMemo, useState } from 'react'
import { BrainCircuit, Braces, GitBranch, Network, Share2, ShieldAlert } from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import type { AnalyticsDistribution, CentralityResult, GraphData, GraphSageAnalysis, GraphSageResult, ModelEvaluation, RiskTrendPoint } from '../types'

const palette = ['#ef6f84', '#5ca9ff', '#9b8cff', '#f18ec7', '#ff8a65', '#45d6b1', '#f6b85b']

export function AnalyticsPage({ graph, investigationId }: { graph: GraphData; investigationId?: string }) {
  const [graphSage, setGraphSage] = useState<GraphSageAnalysis | null>(null)
  const [analytics, setAnalytics] = useState<AnalyticsDistribution | null>(null)
  const [trends, setTrends] = useState<RiskTrendPoint[]>([])
  const [metric, setMetric] = useState<CentralityResult['metric']>('degree')
  const [centrality, setCentrality] = useState<CentralityResult[]>([])
  const [modelEvaluation, setModelEvaluation] = useState<ModelEvaluation | null>(null)
  useEffect(() => {
    let active = true
    Promise.all([api.getGraphSageAnalysis(8), api.getAnalyticsDistribution(), api.getRiskTrends(), api.getModelEvaluation()]).then(([model, distribution, risk, evaluation]) => {
      if (active) { setGraphSage(model); setAnalytics(distribution); setTrends(risk); setModelEvaluation(evaluation) }
    }).catch(() => undefined)
    return () => { active = false }
  }, [graph.nodes.length, graph.edges.length, investigationId])
  useEffect(() => { api.getCentrality(metric, 8, 'person').then(setCentrality).catch(() => undefined) }, [metric, graph.nodes.length, graph.edges.length, investigationId])

  const typeCounts = Object.entries(graph.nodes.reduce<Record<string, number>>((counts, node) => ({ ...counts, [node.type]: (counts[node.type] || 0) + 1 }), {}))
  const entityDistribution = typeCounts.map(([name, value], index) => ({ name: name === 'event' ? 'Incidents' : `${name.charAt(0).toUpperCase()}${name.slice(1)}`, value, color: palette[index % palette.length] }))
  const density = analytics?.structure.density ?? (graph.nodes.length > 1 ? graph.edges.length / (graph.nodes.length * (graph.nodes.length - 1) / 2) : 0)
  const averageDegree = analytics?.structure.average_degree ?? (graph.nodes.length ? graph.edges.length * 2 / graph.nodes.length : 0)
  const componentCount = analytics?.structure.components ?? 0
  const degreeData = (analytics?.degree_distribution ?? []).slice(0, 18).map((item) => ({ ...item, degree: String(item.degree) }))
  const localGraphSagePreview = useMemo<GraphSageResult[]>(() => {
    const cases = new Set(graph.nodes.filter((node) => node.type === 'event').map((node) => node.id))
    const counts = new Map<string, number>()
    graph.edges.forEach((edge) => {
      if (cases.has(edge.source)) counts.set(edge.target, (counts.get(edge.target) || 0) + 1)
      if (cases.has(edge.target)) counts.set(edge.source, (counts.get(edge.source) || 0) + 1)
    })
    return graph.nodes.filter((node) => node.type === 'person').map((node) => ({
      node_id: node.id,
      name: node.name,
      case_neighbors: counts.get(node.id) || 0,
      graph_degree: counts.get(node.id) || 0,
      feature_vector: [],
      derived_label: (counts.get(node.id) || 0) >= 2 ? 'suspicious' as const : 'normal' as const,
      probability: null,
      risk: node.risk,
    })).sort((a, b) => b.case_neighbors - a.case_neighbors || b.risk - a.risk).slice(0, 8)
  }, [graph])
  const graphSageItems = graphSage?.items ?? localGraphSagePreview
  const graphSageStatus = graphSage?.model.status ?? 'checkpoint-required'
  return (
    <div className="standard-page">
      <div className="page-heading"><div><span className="eyebrow">GRAPH INTELLIGENCE</span><h1>Advanced analytics</h1><p>Structural metrics, model outputs, and behavioral distributions.</p></div><select className="page-select"><option>Last 30 days</option><option>Last 7 days</option><option>All time</option></select></div>
      <div className="metrics-strip">
        <div><span><Network size={16}/></span><small>GRAPH DENSITY</small><strong>{density.toFixed(4)}</strong><em>active topology</em></div>
        <div><span><GitBranch size={16}/></span><small>AVG. DEGREE</small><strong>{averageDegree.toFixed(2)}</strong><em>exact edge count</em></div>
        <div><span><Share2 size={16}/></span><small>COMPONENTS</small><strong>{componentCount}</strong><em>connected groups</em></div>
        <div><span><Braces size={16}/></span><small>MODULARITY</small><strong>{(analytics?.structure.modularity ?? 0).toFixed(3)}</strong><em>label partition</em></div>
      </div>
      <div className="analytics-grid">
        <section className="panel chart-wide"><div className="panel-header"><div><span className="eyebrow">TEMPORAL SIGNAL · SOURCE DATES</span><h2>Risk trajectory</h2></div><div className="chart-legend"><span><i className="mint"/>Average risk</span><span><i className="violet"/>Review signals</span></div></div><div className="chart-box"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trends}><defs><linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#45d6b1" stopOpacity={.28}/><stop offset="95%" stopColor="#45d6b1" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false}/><XAxis dataKey="period" tick={{ fill: 'var(--text-faint)', fontSize: 11 }} axisLine={false} tickLine={false}/><YAxis tick={{ fill: 'var(--text-faint)', fontSize: 11 }} axisLine={false} tickLine={false}/><Tooltip contentStyle={{background:'var(--panel-solid)', border:'1px solid var(--border)', borderRadius:8}}/><Area type="monotone" dataKey="average_risk" name="Average risk" stroke="#45d6b1" strokeWidth={2} fill="url(#riskGradient)"/><Area type="monotone" dataKey="review_signals" name="Review signals" stroke="#9b8cff" fill="transparent" strokeDasharray="4 4"/></AreaChart></ResponsiveContainer></div></section>
        <section className="panel distribution-panel"><div className="panel-header"><div><span className="eyebrow">ONTOLOGY MIX</span><h2>Entity types</h2></div></div><div className="donut-wrap"><ResponsiveContainer width="55%" height={190}><PieChart><Pie data={entityDistribution} dataKey="value" innerRadius={53} outerRadius={73} paddingAngle={3} stroke="none">{entityDistribution.map((item) => <Cell key={item.name} fill={item.color}/>)}</Pie><Tooltip contentStyle={{background:'var(--panel-solid)',border:'1px solid var(--border)',borderRadius:8}}/></PieChart></ResponsiveContainer><div className="donut-center"><strong>{graph.nodes.length.toLocaleString()}</strong><span>entities</span></div><div className="distribution-legend">{entityDistribution.map((item) => <span key={item.name}><i style={{background:item.color}}/><b>{item.name}</b><em>{Math.round(item.value / Math.max(1, graph.nodes.length) * 100)}%</em></span>)}</div></div></section>
        <section className="panel degree-panel"><div className="panel-header"><div><span className="eyebrow">NETWORK STRUCTURE · EXACT</span><h2>Degree distribution</h2></div><span className="source-label">{analytics?.structure.max_degree ?? 0} MAX DEGREE</span></div><div className="chart-box compact"><ResponsiveContainer width="100%" height="100%"><BarChart data={degreeData}><CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false}/><XAxis dataKey="degree" tick={{fill:'var(--text-faint)',fontSize:11}} axisLine={false}/><YAxis tick={{fill:'var(--text-faint)',fontSize:11}} axisLine={false}/><Tooltip contentStyle={{background:'var(--panel-solid)',border:'1px solid var(--border)',borderRadius:8}}/><Bar dataKey="nodes" fill="#9b8cff" radius={[3,3,0,0]}/></BarChart></ResponsiveContainer></div></section>
        <section className="panel centrality-panel"><div className="panel-header"><div><span className="eyebrow">KEY-INDIVIDUAL ANALYSIS</span><h2>Influential people</h2></div><select value={metric} onChange={(event) => setMetric(event.target.value as CentralityResult['metric'])}><option value="influence">Composite influence</option><option value="betweenness">Betweenness</option><option value="degree">Degree</option><option value="reach">Neighborhood reach</option></select></div><div className="centrality-list">{centrality.slice(0, 6).map((item)=><div key={item.node.id} title={`${item.method}. Investigative lead only; verify identity and context.`}><span>{item.rank}</span><i className={item.node.type}/><strong>{item.node.name}<small>{item.degree} evidence links</small></strong><div><i style={{width:`${Math.min(100, item.score * 100)}%`}}/></div><em>{item.score.toFixed(3)}</em></div>)}</div></section>
        <section className="panel embedding-panel"><div className="panel-header"><div><span className="eyebrow">DETERMINISTIC VISUAL AID</span><h2>Entity topology field</h2></div><span className="model-chip">NOT AN INFERENCE</span></div><div className="embedding-space">{graph.nodes.slice(0, 58).map((node,i)=><i key={node.id} title={`${node.name} · ${node.type}`} style={{left:`${8+((i*37)%84)}%`,top:`${8+((i*61)%82)}%`,width:`${4+(node.risk%3)*2}px`,height:`${4+(node.risk%3)*2}px`,background:palette[Object.keys(analytics?.entity_types ?? {}).indexOf(node.type) % palette.length] || palette[0],animationDelay:`-${i*.13}s`}}/>)}<span className="cluster-label c1">ACTIVE ENTITIES</span><span className="cluster-label c2">TYPE-COLORED</span><span className="cluster-label c3">DISPLAY ONLY</span></div></section>
        <section className="panel graphsage-panel">
          <div className="panel-header">
            <div><span className="eyebrow">GRAPH NEURAL NETWORK</span><h2>GraphSAGE suspect risk</h2></div>
            <span className={`model-chip ${graphSageStatus === 'ready' ? 'ready' : 'pending'}`}>{graphSageStatus.replace('-', ' ')}</span>
          </div>
          <div className="graphsage-body">
            <div className="graphsage-overview">
              <span className="graphsage-icon"><BrainCircuit size={23}/></span>
              <div><small>MODEL</small><strong>2 × 32</strong><em>message-passing layers</em></div>
              <div><small>FEATURES</small><strong>7</strong><em>6 types + degree</em></div>
              <div><small>TRAINING GRAPH</small><strong>1,530</strong><em>nodes · 2,127 edges</em></div>
              <div><small>PROXY HOLDOUT F1</small><strong>{(modelEvaluation?.graphsage.held_out_node_validation?.metrics.f1 ?? graphSage?.model.training_summary.reproduced_checkpoint?.validation_f1 ?? 0).toFixed(2)}</strong><em>{modelEvaluation?.graphsage.held_out_node_validation?.samples ?? 87} transductive nodes</em></div>
              <div><small>HOLDOUT BRIER</small><strong>{modelEvaluation?.graphsage.held_out_node_validation?.brier_score?.toFixed(3) ?? '—'}</strong><em>structural proxy calibration</em></div>
              <div><small>RISK BASELINE F1</small><strong>{modelEvaluation?.fixed_baselines.risk_score_at_least_70.f1.toFixed(2) ?? '—'}</strong><em>fixed transparent comparator</em></div>
            </div>
            <div className="graphsage-ranking">
              <div className="graphsage-heading"><strong>Top repeat-subject signals</strong><span>{graphSage?.mode === 'graphsage-inference' ? 'MODEL PROBABILITY' : 'STRUCTURAL PREVIEW'}</span></div>
              {graphSageItems.slice(0, 6).map((item) => {
                const signal = item.probability === null ? Math.min(100, item.case_neighbors * 25) : item.probability * 100
                return <div className="graphsage-row" key={item.node_id}><i className={item.derived_label}/><strong>{item.name}<small>{item.case_neighbors} linked case{item.case_neighbors === 1 ? '' : 's'} · degree {item.graph_degree}</small></strong><div><i style={{width:`${signal}%`}}/></div><em>{item.probability === null ? item.derived_label : `${Math.round(signal)}%`}</em></div>
              })}
            </div>
          </div>
          <div className="model-assurance-bar"><ShieldAlert size={21}/><div><small>MODEL CLAIM PASSPORT</small><strong>Field accuracy: {modelEvaluation?.claim_assurance?.field_accuracy?.replaceAll('-', ' ') ?? 'not established'}</strong><p>{modelEvaluation?.claim_assurance?.dependency_explanation ?? 'The structural proxy is not an independently adjudicated operational outcome.'}</p></div><span><small>FEATURE/TARGET DEPENDENCY</small><strong>{modelEvaluation?.claim_assurance?.feature_target_dependency ?? 'HIGH'}</strong></span><span><small>OPERATIONAL RELEASE</small><strong>BLOCKED</strong></span></div>
          <p className="model-note">{graphSage?.message ?? 'GraphSAGE architecture loaded. The trained .pt checkpoint is required before this preview becomes model inference.'} Labels are structural proxies—not independently adjudicated outcomes. Outputs support analyst review and must not be treated as evidence of guilt.</p>
        </section>
      </div>
    </div>
  )
}
