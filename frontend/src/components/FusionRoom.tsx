import { useEffect, useState } from 'react'
import { ArrowRight, Check, CheckCircle2, Database, Eye, Fingerprint, GitMerge, Layers3, Play, Radio, Route, ShieldCheck, TriangleAlert, X } from 'lucide-react'
import { api } from '../api'
import type { IdentityCandidate, SurakshaEvaluation, SurakshaReplay } from '../types'

const shortReceipt = (value?: string | null) => value ? `${value.slice(0, 12)}…${value.slice(-8)}` : 'pending'

export function FusionRoom({ activeId, onActivate, onOpenTrace }: { activeId?: string; onActivate: (id: string) => Promise<void>; onOpenTrace: () => void }) {
  const [replay, setReplay] = useState<SurakshaReplay | null>(null)
  const [evaluation, setEvaluation] = useState<SurakshaEvaluation | null>(null)
  const [candidates, setCandidates] = useState<IdentityCandidate[]>([])
  const [selectedStep, setSelectedStep] = useState(1)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [loadError, setLoadError] = useState('')

  const load = async () => {
    try {
      const [nextReplay, nextEvaluation, nextCandidates] = await Promise.all([api.getSurakshaReplay(), api.getSurakshaEvaluation(), api.getIdentityCandidates()])
      setReplay(nextReplay); setEvaluation(nextEvaluation); setCandidates(nextCandidates); setLoadError('')
    } catch {
      setLoadError('The local evidence service is unavailable. Start the backend and retry.')
    }
  }

  useEffect(() => { void load() }, [])

  const activate = async () => {
    setBusy(true)
    try {
      await onActivate('operation-suraksha')
      setMessage('Flagship investigation activated.')
    } catch {
      setMessage('Activation failed. Check the local backend and retry.')
    } finally {
      setBusy(false)
    }
  }

  const decide = async (candidate: IdentityCandidate, decision: 'keep-separate' | 'escalate') => {
    setBusy(true)
    const rationale = decision === 'keep-separate'
      ? 'Distinct phones and conflicting near-simultaneous locations outweigh name similarity.'
      : 'Additional immutable source identifiers are required before any identity decision.'
    try {
      await api.decideIdentityCandidate(candidate.id, decision, rationale)
      await load()
      setMessage(decision === 'keep-separate' ? 'Separate identities preserved and decision receipted.' : 'Candidate escalated for source verification.')
    } catch {
      setMessage('Decision could not be recorded. Check the local backend and retry.')
    } finally {
      setBusy(false)
    }
  }

  const current = replay?.steps.find((step) => step.order === selectedStep) ?? replay?.steps[0]
  const candidate = candidates[0]
  const summary = evaluation?.summary

  return (
    <div className="standard-page fusion-page">
      <div className="page-heading fusion-heading">
        <div><span className="eyebrow">FLAGSHIP MULTI-SOURCE EXERCISE</span><h1>Operation Suraksha</h1><p>Watch disconnected evidence become a challengeable investigation graph—without cloud services or fabricated certainty.</p></div>
        <div className="fusion-heading-actions"><span className="synthetic-pill"><ShieldCheck size={13}/> SYNTHETIC · SAFE DEMO</span>{activeId !== 'operation-suraksha' ? <button className="primary-button" disabled={busy} onClick={activate}><Play size={14}/>{busy ? 'Activating…' : 'Activate flagship case'}</button> : <span className="active-case-pill"><Check size={13}/> ACTIVE INVESTIGATION</span>}</div>
      </div>

      {loadError && <section className="panel fusion-load-error" role="alert"><TriangleAlert size={18}/><span>{loadError}</span><button className="secondary-button" onClick={() => void load()}>Retry</button></section>}

      <section className="panel fusion-hero">
        <div className="fusion-orbit" aria-hidden="true"><span className="core-node">TRACE</span>{['FIR','CDR','BANK','ANPR','SURV','OSINT'].map((source, index) => <i key={source} style={{'--i': index} as React.CSSProperties}><b>{source}</b></i>)}</div>
        <div className="fusion-hero-copy"><span className="eyebrow">CROSS-SOURCE FUSION</span><h2>One case. Six evidence channels. Every inference inspectable.</h2><p>The scenario contains a hidden multi-hop network, a circular account path, time-window co-location, a bridge entity, and a deliberate identity trap. All people, identifiers, events, and organizations are fictional.</p><div className="fusion-source-counts">{Object.entries(replay?.source_counts ?? {}).map(([source,count]) => <span key={source}><strong>{count}</strong>{source}</span>)}</div><div className="fusion-hero-actions"><button className="primary-button" onClick={() => setSelectedStep(Math.min((replay?.steps.length ?? 1), selectedStep + 1))}><Play size={14}/> Reveal next signal</button><button className="secondary-button" onClick={onOpenTrace}><Route size={14}/> Open path proof</button></div>{message && <small className="fusion-message"><CheckCircle2 size={12}/>{message}</small>}</div>
        <div className="fusion-scorecard"><span className="eyebrow">GROUND-TRUTH HARNESS</span><div><strong>{summary?.entities_recovered ?? '—'}<small>/{summary?.entities_expected ?? '—'}</small></strong><span>Entity checkpoints</span><i className="pass"><Check size={12}/></i></div><div><strong>{summary?.relationships_recovered ?? '—'}<small>/{summary?.relationships_expected ?? '—'}</small></strong><span>Relation checkpoints</span><i className="pass"><Check size={12}/></i></div><div><strong>{summary?.hidden_path_recovered ? 'YES' : '—'}</strong><span>Hidden path recovered</span><i className="pass"><Route size={12}/></i></div><div><strong>{summary?.false_merges ?? '—'}</strong><span>False identity merges</span><i className="safe"><ShieldCheck size={12}/></i></div><p>{evaluation?.scope_note}</p><code title={evaluation?.receipt}><Fingerprint size={11}/>{shortReceipt(evaluation?.receipt)}</code></div>
      </section>

      <div className="fusion-layout">
        <section className="panel replay-panel">
          <div className="panel-header"><div><span className="eyebrow">INVESTIGATION REPLAY</span><h2>Evidence-to-insight sequence</h2></div><span className="source-label">{replay?.steps.length ?? 0} VERIFIED STAGES</span></div>
          <div className="replay-body">
            <div className="replay-rail">{replay?.steps.map((step) => <button key={step.order} className={`${selectedStep === step.order ? 'active' : ''} ${step.status}`} onClick={() => setSelectedStep(step.order)}><span>{String(step.order).padStart(2,'0')}</span><i/><div><small>{step.time} · {step.source}</small><strong>{step.title}</strong></div></button>)}</div>
            {current && <article className="replay-detail"><div className="replay-detail-top"><span className={`trace-status ${current.status === 'observation' ? 'verified' : ''}`}>{current.status.replace('-', ' ')}</span><code title={current.receipt}>{shortReceipt(current.receipt)}</code></div><span className="replay-icon">{current.status === 'observation' ? <Database size={25}/> : current.status === 'human-review' ? <ShieldCheck size={25}/> : <Layers3 size={25}/>}</span><small>STAGE {String(current.order).padStart(2,'0')} · {current.source}</small><h3>{current.title}</h3><p>{current.finding}</p><div className="evidence-id-list"><span><Fingerprint size={12}/> SOURCE-BACKED OBJECTS</span>{current.evidence_ids.map((id) => <code key={id}>{id}</code>)}</div>{current.order < (replay?.steps.length ?? 0) && <button className="secondary-button" onClick={() => setSelectedStep(current.order + 1)}>Continue replay <ArrowRight size={13}/></button>}</article>}
          </div>
          <p className="trace-guardrail"><ShieldCheck size={14}/>{replay?.guardrail}</p>
        </section>

        <section className="panel identity-lab">
          <div className="panel-header"><div><span className="eyebrow">ENTITY RESOLUTION CONTROL</span><h2>Prevent the dangerous merge</h2></div><GitMerge size={18}/></div>
          {candidate && <div className="identity-body">
            <div className="identity-pair"><button><i className="person"/><span>{candidate.left.name}<small>{candidate.left.id}</small></span></button><div><strong>{Math.round(candidate.similarity * 100)}%</strong><span>NAME-LEVEL CANDIDATE</span><i/></div><button><i className="person"/><span>{candidate.right.name}<small>{candidate.right.id}</small></span></button></div>
            <div className="identity-signals"><div className="support"><span><CheckCircle2 size={13}/> SUPPORTING</span>{candidate.supporting_signals.map((signal) => <p key={signal}>{signal}</p>)}</div><div className="conflict"><span><TriangleAlert size={13}/> CONTRADICTING</span>{candidate.conflicting_signals.map((signal) => <p key={signal}>{signal}</p>)}</div></div>
            <div className="identity-recommendation"><ShieldCheck size={20}/><div><small>SYSTEM RECOMMENDATION</small><strong>{candidate.recommendation.replace('-', ' ')}</strong><p>{candidate.guardrail}</p></div></div>
            {candidate.decision ? <div className="identity-decided"><Check size={15}/><span><strong>{candidate.decision.effect}</strong><small>{candidate.decision.rationale}</small></span></div> : <div className="identity-actions"><button disabled={busy} onClick={() => void decide(candidate,'keep-separate')}><X size={14}/> Keep separate</button><button disabled={busy} onClick={() => void decide(candidate,'escalate')}><Eye size={14}/> Request verification</button></div>}
            <div className="trace-receipt"><Fingerprint size={14}/><span><small>CANDIDATE RECEIPT</small><code title={candidate.receipt}>{shortReceipt(candidate.receipt)}</code></span></div>
          </div>}
        </section>
      </div>

      <section className="panel fusion-assurance"><div><Radio size={18}/><span><strong>NO LIVE COLLECTION</strong><small>All six channels are synthetic fixtures</small></span></div><div><Database size={18}/><span><strong>LOCAL PROCESSING</strong><small>No paid API or hosted database required</small></span></div><div><Fingerprint size={18}/><span><strong>REPRODUCIBLE</strong><small>Every replay stage carries a receipt</small></span></div><div><ShieldCheck size={18}/><span><strong>HUMAN AUTHORITY</strong><small>No automated identity or enforcement decision</small></span></div></section>
    </div>
  )
}
