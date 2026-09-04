import { useEffect, useState } from 'react'
import { Activity, ArrowRight, Check, CheckCircle2, Database, Eye, Fingerprint, GitMerge, KeyRound, Layers3, LockKeyhole, Play, Radio, RefreshCcw, Route, ScanSearch, ShieldCheck, TriangleAlert, X } from 'lucide-react'
import { api } from '../api'
import type { AuditVerification, FusionAssurance, IdentityCandidate, ProtectedProfile, ScaleBenchmark, SurakshaEvaluation, SurakshaReplay, SystemReadiness, TemporalEmergence } from '../types'

const shortReceipt = (value?: string | null) => value ? `${value.slice(0, 12)}…${value.slice(-8)}` : 'pending'

export function FusionRoom({ activeId, onActivate, onOpenTrace }: { activeId?: string; onActivate: (id: string) => Promise<void>; onOpenTrace: () => void }) {
  const [replay, setReplay] = useState<SurakshaReplay | null>(null)
  const [evaluation, setEvaluation] = useState<SurakshaEvaluation | null>(null)
  const [candidates, setCandidates] = useState<IdentityCandidate[]>([])
  const requestedStage = Number(new URLSearchParams(window.location.search).get('stage') || 1)
  const privacyFocus = new URLSearchParams(window.location.search).get('focus') === 'privacy'
  const [selectedStep, setSelectedStep] = useState(Number.isFinite(requestedStage) ? Math.min(6, Math.max(1, requestedStage)) : 1)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [loadError, setLoadError] = useState('')
  const [protectedPeople, setProtectedPeople] = useState<ProtectedProfile[]>([])
  const [revealedProfile, setRevealedProfile] = useState<ProtectedProfile | null>(null)
  const [revealReason, setRevealReason] = useState('Verify protected contact details for authorized synthetic case review')
  const [authorizationReference, setAuthorizationReference] = useState('DEMO-AUTH-001')
  const [audit, setAudit] = useState<AuditVerification | null>(null)
  const [readiness, setReadiness] = useState<SystemReadiness | null>(null)
  const [benchmark, setBenchmark] = useState<ScaleBenchmark | null>(null)
  const [fusionAssurance, setFusionAssurance] = useState<FusionAssurance | null>(null)
  const [emergence, setEmergence] = useState<TemporalEmergence | null>(null)

  const load = async () => {
    try {
      const [nextReplay, nextEvaluation, nextCandidates, nextProtected, nextAudit, nextReadiness, nextBenchmark, nextFusion, nextEmergence] = await Promise.all([
        api.getSurakshaReplay(), api.getSurakshaEvaluation(), api.getIdentityCandidates(), api.getProtectedPeople(),
        api.getAuditVerification(), api.getReadiness(), api.getScaleBenchmark().catch(() => null), api.getSurakshaFusionAssurance(), api.getSurakshaEmergence(),
      ])
      setReplay(nextReplay); setEvaluation(nextEvaluation); setCandidates(nextCandidates); setProtectedPeople(nextProtected)
      setAudit(nextAudit); setReadiness(nextReadiness); setBenchmark(nextBenchmark); setFusionAssurance(nextFusion); setEmergence(nextEmergence); setLoadError('')
    } catch {
      setLoadError('The local evidence service is unavailable. Start the backend and retry.')
    }
  }

  useEffect(() => { void load() }, [])
  useEffect(() => {
    if (window.location.hash === '#privacy-controls' && protectedPeople.length) {
      document.getElementById('privacy-controls')?.scrollIntoView({ behavior: 'auto', block: 'start' })
    }
  }, [protectedPeople])

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

  const startGuidedDemo = () => {
    setSelectedStep(1)
    setRevealedProfile(null)
    setMessage('Guided demonstration ready at stage one.')
    document.querySelector('.replay-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const resetDemo = async () => {
    setBusy(true)
    try {
      await api.resetSuraksha()
      setSelectedStep(1); setRevealedProfile(null)
      await load()
      setMessage('Operation Suraksha reset: decisions cleared, evidence unchanged, stage one restored.')
    } catch {
      setMessage('Reset failed. Check the evidence service and retry.')
    } finally {
      setBusy(false)
    }
  }

  const reveal = async () => {
    const profile = protectedPeople[0]
    if (!profile) return
    setBusy(true)
    try {
      const revealed = await api.revealProtectedPerson(profile.id, revealReason, authorizationReference)
      setRevealedProfile(revealed)
      const [nextAudit, nextReadiness] = await Promise.all([api.getAuditVerification(), api.getReadiness()])
      setAudit(nextAudit); setReadiness(nextReadiness)
      setMessage('Synthetic protected identity revealed for this response and recorded in the audit chain.')
    } catch {
      setMessage('Reveal requires a reason of at least 10 characters and an authorization reference.')
    } finally {
      setBusy(false)
    }
  }

  const current = replay?.steps.find((step) => step.order === selectedStep) ?? replay?.steps[0]
  const candidate = candidates[0]
  const summary = evaluation?.summary

  return (
    <div className={`standard-page fusion-page ${privacyFocus ? 'focus-privacy' : ''}`}>
      <div className="page-heading fusion-heading">
        <div><span className="eyebrow">FLAGSHIP MULTI-SOURCE EXERCISE</span><h1>Operation Suraksha</h1><p>Watch disconnected evidence become a challengeable investigation graph—without cloud services or fabricated certainty.</p></div>
        <div className="fusion-heading-actions"><span className="synthetic-pill"><ShieldCheck size={13}/> SYNTHETIC · SAFE DEMO</span><button className="secondary-button" disabled={busy} onClick={startGuidedDemo}><Play size={14}/> Guided demo</button><button className="secondary-button" disabled={busy} onClick={() => void resetDemo()}><RefreshCcw size={14}/> Reset</button>{activeId !== 'operation-suraksha' ? <button className="primary-button" disabled={busy} onClick={activate}><Play size={14}/>{busy ? 'Activating…' : 'Activate case'}</button> : <span className="active-case-pill"><Check size={13}/> ACTIVE INVESTIGATION</span>}</div>
      </div>

      {loadError && <section className="panel fusion-load-error" role="alert"><TriangleAlert size={18}/><span>{loadError}</span><button className="secondary-button" onClick={() => void load()}>Retry</button></section>}

      <section className="panel fusion-hero">
        <div className="fusion-orbit" aria-hidden="true"><span className="core-node">TRACE</span>{['FIR','CDR','BANK','ANPR','SURV','OSINT'].map((source, index) => <i key={source} style={{'--i': index} as React.CSSProperties}><b>{source}</b></i>)}</div>
        <div className="fusion-hero-copy"><span className="eyebrow">CROSS-SOURCE FUSION</span><h2>One case. Six evidence channels. Every inference inspectable.</h2><p>The scenario contains a hidden multi-hop network, a circular account path, time-window co-location, a bridge entity, and a deliberate identity trap. All people, identifiers, events, and organizations are fictional.</p><div className="fusion-source-counts">{Object.entries(replay?.source_counts ?? {}).map(([source,count]) => <span key={source}><strong>{count}</strong>{source}</span>)}</div><div className="fusion-hero-actions"><button className="primary-button" onClick={() => setSelectedStep(Math.min((replay?.steps.length ?? 1), selectedStep + 1))}><Play size={14}/> Reveal next signal</button><button className="secondary-button" onClick={onOpenTrace}><Route size={14}/> Open path proof</button></div>{message && <small className="fusion-message"><CheckCircle2 size={12}/>{message}</small>}</div>
        <div className="fusion-scorecard"><span className="eyebrow">GROUND-TRUTH HARNESS</span><div><strong>{summary?.entities_recovered ?? '—'}<small>/{summary?.entities_expected ?? '—'}</small></strong><span>Entity checkpoints</span><i className="pass"><Check size={12}/></i></div><div><strong>{summary?.relationships_recovered ?? '—'}<small>/{summary?.relationships_expected ?? '—'}</small></strong><span>Relation checkpoints</span><i className="pass"><Check size={12}/></i></div><div><strong>{summary?.hidden_path_recovered ? 'YES' : '—'}</strong><span>Hidden path recovered</span><i className="pass"><Route size={12}/></i></div><div><strong>{summary?.false_merges ?? '—'}</strong><span>False identity merges</span><i className="safe"><ShieldCheck size={12}/></i></div><p>{evaluation?.scope_note}</p><code title={evaluation?.receipt}><Fingerprint size={11}/>{shortReceipt(evaluation?.receipt)}</code></div>
      </section>

      <section className="panel fusion-validation-panel">
        <div className="panel-header"><div><span className="eyebrow">COMPUTED FROM SOURCE RECORDS</span><h2>Cross-source pattern assurance</h2></div><span className="source-label"><ScanSearch size={12}/>{fusionAssurance?.summary.patterns_recovered ?? '—'}/{fusionAssurance?.summary.patterns_expected ?? '—'} PATTERNS RECOVERED</span></div>
        <div className="fusion-validation-summary">
          <div><small>ACCEPTANCE CHECKS</small><strong>{fusionAssurance?.summary.checks_passed ?? '—'}/{fusionAssurance?.summary.checks_total ?? '—'}</strong><span>machine-verifiable</span></div>
          <div><small>EDGE PROVENANCE</small><strong>{fusionAssurance?.summary.edge_provenance_coverage ?? '—'}%</strong><span>source record + channel</span></div>
          <div><small>EVIDENCE CHANNELS</small><strong>{fusionAssurance?.summary.source_channels ?? '—'}</strong><span>independently classified</span></div>
          <div><small>FIELD CLAIM</small><strong>NOT CLAIMED</strong><span>synthetic acceptance only</span></div>
        </div>
        <div className="fusion-pattern-grid">{fusionAssurance?.patterns.map((pattern) => <article key={pattern.id} className={pattern.severity}>
          <div><span className={`pattern-severity ${pattern.severity}`}>{pattern.severity}</span><code title={pattern.receipt}><Fingerprint size={10}/>{shortReceipt(pattern.receipt)}</code></div>
          <h3>{pattern.title}</h3><p>{pattern.explanation}</p>
          <div className="pattern-sources">{pattern.source_types.map((source) => <span key={source}>{source}</span>)}</div>
          <small><strong>{pattern.evidence_record_ids.length} source objects</strong> · {pattern.evidence_record_ids.slice(0, 4).join(' · ')}{pattern.evidence_record_ids.length > 4 ? ' …' : ''}</small>
          <details><summary>Challenge this lead</summary><p><strong>Alternative:</strong> {pattern.alternative}</p><p><strong>Next action:</strong> {pattern.analyst_action}</p><p className="pattern-digests"><strong>Record receipts:</strong> {pattern.evidence_records.slice(0, 3).map((record) => `${record.id} ${record.sha256.slice(0, 8)}…`).join(' · ')}</p></details>
        </article>)}</div>
        <p className="trace-guardrail"><ShieldCheck size={14}/>{fusionAssurance?.scope_note}</p>
      </section>

      <section className="panel emergence-panel">
        <div className="panel-header"><div><span className="eyebrow">TEMPORAL KNOWLEDGE GRAPH</span><h2>How the network emerged</h2></div><span className="source-label"><Activity size={12}/> TIMESTAMP RECONSTRUCTION</span></div>
        <div className="emergence-track">{emergence?.snapshots.map((snapshot, index) => <div key={snapshot.date} className={snapshot.new_patterns.length ? 'milestone' : ''}>
          <span>{new Date(`${snapshot.date}T00:00:00`).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}</span><i/><strong>{snapshot.cumulative_nodes} entities</strong><small>{snapshot.cumulative_records} records · {snapshot.source_types_seen.length} channels</small><em>{snapshot.new_patterns.length ? `+ ${snapshot.new_patterns.map((item) => item.replaceAll('-', ' ')).join(', ')}` : index === 0 ? 'first preserved records' : 'evidence accumulated'}</em>
        </div>)}</div>
        <div className="trace-receipt"><Fingerprint size={14}/><span><small>EMERGENCE RECEIPT</small><code title={emergence?.receipt}>{shortReceipt(emergence?.receipt)}</code></span></div>
        <p className="trace-guardrail"><ShieldCheck size={14}/>{emergence?.guardrail}</p>
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

      <div className="fusion-controls-grid" id="privacy-controls">
        <section className="panel privacy-control-panel">
          <div className="panel-header"><div><span className="eyebrow">PROTECTED-PERSON PRIVACY</span><h2>Masked by default. Never scored.</h2></div><LockKeyhole size={18}/></div>
          <p className="privacy-intro">Protected people are separate entity types. Their graph labels stay pseudonymized, risk remains zero, and GraphSAGE never receives their nodes.</p>
          {protectedPeople[0] && <div className="protected-profile">
            <div className="masked-profile"><span><LockKeyhole size={18}/></span><div><small>{protectedPeople[0].graph_name}</small><strong>{revealedProfile?.name ?? protectedPeople[0].name}</strong><p>{revealedProfile?.phone ?? protectedPeople[0].phone} · {revealedProfile?.address ?? protectedPeople[0].address}</p></div><em>{revealedProfile ? 'EPHEMERAL REVEAL' : 'MASKED'}</em></div>
            <label>Reason for access<textarea value={revealReason} onChange={(event) => setRevealReason(event.target.value)} /></label>
            <label>Authorization reference<input value={authorizationReference} onChange={(event) => setAuthorizationReference(event.target.value)} /></label>
            <div className="privacy-actions"><button className="secondary-button" disabled={busy || revealReason.trim().length < 10 || authorizationReference.trim().length < 3} onClick={() => void reveal()}><KeyRound size={14}/> Reveal synthetic identity</button>{revealedProfile && <button className="secondary-button" onClick={() => setRevealedProfile(null)}><LockKeyhole size={14}/> Mask again</button>}</div>
            <small className="privacy-footnote">The reason is hashed in the audit event; protected details never enter graph exports.</small>
          </div>}
        </section>

        <section className="panel assurance-control-panel">
          <div className="panel-header"><div><span className="eyebrow">OFFLINE & INTEGRITY READINESS</span><h2>{readiness?.ready ? 'Ready for guided judging' : 'Readiness checks pending'}</h2></div>{readiness?.ready ? <CheckCircle2 className="pass-icon" size={19}/> : <TriangleAlert size={19}/>}</div>
          <div className="readiness-summary"><div><small>OFFLINE</small><strong>{readiness?.offline_capable ? 'YES' : '—'}</strong></div><div><small>AUDIT CHAIN</small><strong>{audit?.valid ? 'VALID' : 'CHECK'}</strong></div><div><small>CHAINED EVENTS</small><strong>{audit?.entries ?? '—'}</strong></div><div><small>PAID APIS</small><strong>{readiness?.external_services_required ? 'REQUIRED' : 'NONE'}</strong></div></div>
          <div className="readiness-checks">{readiness?.checks.map((check) => <span key={check.id} className={check.passed ? 'passed' : 'failed'}>{check.passed ? <Check size={12}/> : <X size={12}/>}<strong>{check.label}</strong><small>{check.detail}</small></span>)}</div>
          {benchmark && <div className="benchmark-strip"><span><Database size={15}/><strong>SCALE PROOF</strong></span>{benchmark.runs.map((run) => <div key={run.records}><strong>{(run.records / 1000).toFixed(0)}K</strong><small>{run.graph_build_seconds}s build · {run.peak_python_memory_mib} MiB peak · {run.connection_path.p95_ms} ms path p95</small></div>)}</div>}
          <div className="audit-head"><Fingerprint size={13}/><span><small>SHA-256 CHAIN HEAD</small><code title={audit?.head}>{shortReceipt(audit?.head)}</code></span><button className="secondary-button" onClick={() => void load()}>Verify chain</button></div>
        </section>
      </div>

      <section className="panel fusion-assurance"><div><Radio size={18}/><span><strong>NO LIVE COLLECTION</strong><small>All six channels are synthetic fixtures</small></span></div><div><Database size={18}/><span><strong>LOCAL PROCESSING</strong><small>No paid API or hosted database required</small></span></div><div><Fingerprint size={18}/><span><strong>REPRODUCIBLE</strong><small>Every replay stage carries a receipt</small></span></div><div><ShieldCheck size={18}/><span><strong>HUMAN AUTHORITY</strong><small>No automated identity or enforcement decision</small></span></div></section>
    </div>
  )
}
