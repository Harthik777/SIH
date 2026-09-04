import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, Clock3, Fingerprint, GitCompareArrows, RefreshCw, Route, ShieldCheck, TriangleAlert } from 'lucide-react'
import { api } from '../api'
import type { ConnectionPath, CounterfactualResult, GraphData, GraphNode, MotifResponse } from '../types'

const shortReceipt = (receipt?: string) => receipt ? `${receipt.slice(0, 12)}…${receipt.slice(-8)}` : 'pending'

function defaultPair(graph: GraphData): [string, string] {
  const flagshipSource = graph.nodes.find((node) => node.name === 'Subject A-17')
  const flagshipTarget = graph.nodes.find((node) => node.name === 'Coordinator C-04')
  if (flagshipSource && flagshipTarget) return [flagshipSource.id, flagshipTarget.id]
  const source = [...graph.nodes].sort((a, b) => (a.type === 'person' ? -1 : 0) - (b.type === 'person' ? -1 : 0) || b.risk - a.risk)[0]
  if (!source) return ['', '']
  const byId = new Map(graph.nodes.map((node) => [node.id, node]))
  const firstEdge = graph.edges.find((edge) => edge.source === source.id || edge.target === source.id)
  const firstId = firstEdge ? (firstEdge.source === source.id ? firstEdge.target : firstEdge.source) : ''
  const secondEdge = firstId && graph.edges.find((edge) => {
    if (edge.source !== firstId && edge.target !== firstId) return false
    const other = edge.source === firstId ? edge.target : edge.source
    return other !== source.id && ['crime', 'location', 'organization'].includes(byId.get(other)?.type ?? '')
  })
  const target = secondEdge ? (secondEdge.source === firstId ? secondEdge.target : secondEdge.source) : firstId
  return [source.id, target]
}

export function TraceLab({ graph, investigationId, onSelect }: { graph: GraphData; investigationId?: string; onSelect: (node: GraphNode) => void }) {
  const [sourceId, setSourceId] = useState('')
  const [targetId, setTargetId] = useState('')
  const [path, setPath] = useState<ConnectionPath | null>(null)
  const [counterfactual, setCounterfactual] = useState<CounterfactualResult | null>(null)
  const [motifs, setMotifs] = useState<MotifResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const orderedNodes = useMemo(() => [...graph.nodes].sort((a, b) => a.type.localeCompare(b.type) || a.name.localeCompare(b.name)), [graph.nodes])

  useEffect(() => {
    const [source, target] = defaultPair(graph)
    setSourceId(source)
    setTargetId(target)
    setPath(null)
    setCounterfactual(null)
    api.getMotifs(25).then(setMotifs).catch(() => setError('TRACE motifs are temporarily unavailable.'))
  }, [graph, investigationId])

  useEffect(() => {
    if (!sourceId || !targetId) return
    let active = true
    setLoading(true)
    setError('')
    Promise.all([api.getConnectionPath(sourceId, targetId), api.getCounterfactual(sourceId)])
      .then(([nextPath, nextCounterfactual]) => {
        if (active) { setPath(nextPath); setCounterfactual(nextCounterfactual) }
      })
      .catch(() => { if (active) setError('The selected trace could not be computed.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [sourceId, targetId, investigationId])

  const refresh = () => {
    if (!sourceId || !targetId) return
    setLoading(true)
    setError('')
    Promise.all([api.getConnectionPath(sourceId, targetId), api.getCounterfactual(sourceId), api.getMotifs(25)])
      .then(([nextPath, nextCounterfactual, nextMotifs]) => { setPath(nextPath); setCounterfactual(nextCounterfactual); setMotifs(nextMotifs) })
      .catch(() => setError('The selected trace could not be computed.'))
      .finally(() => setLoading(false))
  }

  return (
    <div className="standard-page trace-page">
      <div className="page-heading trace-heading">
        <div><span className="eyebrow">PROOF-CARRYING GRAPH INTELLIGENCE</span><h1>TRACE Lab</h1><p>Interrogate relationships and temporal patterns without hiding evidence, uncertainty, or assumptions.</p></div>
        <div className="trace-assurance"><span><ShieldCheck size={13}/> LOCAL ONLY</span><span><Route size={13}/> OBSERVED PATHS</span><span><Fingerprint size={13}/> SHA-256 RECEIPTS</span></div>
      </div>

      <section className="panel trace-builder">
        <div className="trace-builder-copy"><span className="eyebrow">CONNECTION PROVER</span><h2>Show the evidence chain</h2><p>TRACE walks only relationships already stored in the active graph. It never turns similarity into a fact.</p></div>
        <div className="trace-selectors">
          <label><span>FROM ENTITY</span><select value={sourceId} onChange={(event) => setSourceId(event.target.value)}>{orderedNodes.map((node) => <option key={node.id} value={node.id}>{node.type.toUpperCase()} · {node.name}</option>)}</select></label>
          <ArrowRight size={17}/>
          <label><span>TO ENTITY</span><select value={targetId} onChange={(event) => setTargetId(event.target.value)}>{orderedNodes.filter((node) => node.id !== sourceId).map((node) => <option key={node.id} value={node.id}>{node.type.toUpperCase()} · {node.name}</option>)}</select></label>
          <button className="primary-button" onClick={refresh} disabled={loading}><RefreshCw size={14} className={loading ? 'spin' : ''}/>{loading ? 'Tracing…' : 'Recompute'}</button>
        </div>
      </section>

      {error && <div className="trace-error"><TriangleAlert size={15}/>{error}</div>}

      <div className="trace-grid">
        <section className="panel trace-path-panel">
          <div className="panel-header"><div><span className="eyebrow">OBSERVED EVIDENCE</span><h2>Connection path</h2></div>{path && <span className={`trace-status ${path.found ? 'verified' : 'missing'}`}>{path.epistemic_status.replaceAll('-', ' ')}</span>}</div>
          {path?.found ? <>
            <div className="trace-path-summary"><div><small>HOPS</small><strong>{path.hops}</strong></div><div><small>COMPOUND CONFIDENCE</small><strong>{path.path_confidence?.toFixed(1)}%</strong></div><div><small>METHOD</small><strong>{path.method}</strong></div></div>
            <div className="trace-steps">{path.steps.map((step, index) => <div className="trace-step" key={step.edge_id}>
              <button onClick={() => onSelect(step.from)}><i className={step.from.type}/><span>{step.from.name}<small>{step.from.type}</small></span></button>
              <div><span>{step.relationship}</span><i/><small>{step.confidence}% · {step.direction}</small></div>
              <button onClick={() => onSelect(step.to)}><i className={step.to.type}/><span>{step.to.name}<small>{step.to.type}</small></span></button>
              <em>{String(index + 1).padStart(2, '0')}</em>
            </div>)}</div>
          </> : <div className="trace-empty"><Route size={26}/><strong>{loading ? 'Tracing stored relationships…' : 'No observed path inside the hop limit'}</strong><p>Absence of a path is preserved as a result; TRACE does not manufacture a relationship.</p></div>}
          {path && <div className="trace-receipt"><Fingerprint size={14}/><span><small>REPRODUCIBILITY RECEIPT</small><code title={path.receipt}>{shortReceipt(path.receipt)}</code></span></div>}
          {path?.guardrail && <p className="trace-guardrail"><ShieldCheck size={14}/>{path.guardrail}</p>}
        </section>

        <section className="panel counterfactual-panel">
          <div className="panel-header"><div><span className="eyebrow">ASSUMPTION STRESS TEST</span><h2>What would change the score?</h2></div><GitCompareArrows size={18}/></div>
          {counterfactual && <>
            <button className="counterfactual-entity" onClick={() => onSelect(counterfactual.entity)}><i className={counterfactual.entity.type}/><span>{counterfactual.entity.name}<small>CURRENT RISK</small></span><strong>{counterfactual.entity.risk}</strong></button>
            <div className="factor-list">{counterfactual.factors.map((factor) => <div key={factor.factor}><span>{factor.factor}<small>{factor.kind} basis</small></span><strong>{factor.value}</strong></div>)}</div>
            <div className="scenario-list">{counterfactual.scenarios.map((scenario) => <article key={scenario.change}><div><span>{counterfactual.entity.risk}</span><ArrowRight size={13}/><strong>{scenario.risk_after}</strong><em>{scenario.delta}</em></div><p>{scenario.change}</p><small>{scenario.required_verification}</small></article>)}</div>
            <div className="trace-receipt"><Fingerprint size={14}/><span><small>SCENARIO RECEIPT</small><code title={counterfactual.receipt}>{shortReceipt(counterfactual.receipt)}</code></span></div>
            <p className="trace-guardrail"><ShieldCheck size={14}/>{counterfactual.guardrail}</p>
          </>}
        </section>
      </div>

      <div className="section-heading"><div><span className="eyebrow">TEMPORAL MOTIF RADAR</span><h2>Patterns requiring corroboration</h2></div><small>{motifs?.total ?? 0} source-derived leads · never automatic accusations</small></div>
      <div className="motif-grid">{motifs?.items.slice(0, 9).map((motif) => <article className="panel motif-card" key={motif.id}>
        <div className="motif-top"><span className={`severity ${motif.severity}`}>{motif.severity}</span><code title={motif.receipt}>{shortReceipt(motif.receipt)}</code></div>
        <button onClick={() => onSelect(motif.subject)}><i className={motif.subject.type}/><span><strong>{motif.title}</strong><small>{motif.type.replaceAll('-', ' ')}</small></span></button>
        <p>{motif.summary}</p>
        <div className="motif-metrics"><span><strong>{motif.case_ids.length}</strong> cases</span><span><strong>{motif.location_ids.length}</strong> locations</span>{motif.minimum_gap_days !== null && <span><Clock3 size={12}/><strong>{motif.minimum_gap_days}d</strong> min gap</span>}</div>
        <div className="motif-alternative"><TriangleAlert size={13}/><span><small>ALTERNATIVE EXPLANATION</small>{motif.alternative}</span></div>
      </article>)}</div>
      {motifs && <p className="trace-global-guardrail"><ShieldCheck size={14}/>{motifs.guardrail}<code title={motifs.receipt}>{shortReceipt(motifs.receipt)}</code></p>}
    </div>
  )
}
