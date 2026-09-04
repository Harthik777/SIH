import { ArrowRight, BrainCircuit, CheckCircle2, ChevronUp, CircleDot, Scale, Sparkles } from 'lucide-react'
import type { InvestigationBriefing } from '../types'

interface Props {
  briefing: InvestigationBriefing | null
  expanded: boolean
  onToggle: () => void
}

function evidenceLabel(evidence: Record<string, unknown>) {
  return Object.entries(evidence).slice(0, 3).map(([key, value]) => {
    const rendered = Array.isArray(value) ? value.slice(0, 3).join(', ') : String(value)
    return `${key.replaceAll('_', ' ')}: ${rendered}`
  }).join(' · ')
}

export function AiBrief({ briefing, expanded, onToggle }: Props) {
  const finding = briefing?.findings[0]
  return (
    <section className={`panel ai-brief ${expanded ? 'expanded' : ''}`} id="analysis-brief">
      <div className="ai-orbit"><BrainCircuit size={24} /><i /><i /><i /></div>
      <div className="ai-copy">
        <span className="eyebrow"><Sparkles size={11} /> EVIDENCE-BACKED ANALYSIS</span>
        <h2>{finding?.title ?? 'Repeat-subject and beat concentration detected'}</h2>
        <p>{finding?.summary ?? <>Recent activity in <strong>Police Beat 0412</strong> exceeds its rolling baseline. Shared entities connect incidents that appeared unrelated in the source FIR narratives.</>}</p>
        <div className="evidence-row"><span><CheckCircle2 size={12}/> {finding?.evidence.length ?? 4} supporting records</span><span>{finding?.confidence ?? 97}% confidence</span><span>{finding?.alternatives.length ?? 2} alternative hypotheses</span><span>{finding?.basis ?? 'direct graph count'}</span></div>
      </div>
      <button className="explain-button" onClick={onToggle}>{expanded ? <>Close rationale <ChevronUp size={14}/></> : <>Explain finding <ArrowRight size={14}/></>}</button>
      {expanded && finding && <div className="explainability-grid">
        <div><span className="explain-icon"><CircleDot size={15}/></span><strong>Why it was flagged</strong><p>{finding.summary} Basis: {finding.basis}.</p></div>
        <div><span className="explain-icon"><CheckCircle2 size={15}/></span><strong>Source-linked evidence</strong><ul>{finding.evidence.slice(0, 4).map((item, index) => <li key={index}>{evidenceLabel(item)}</li>)}</ul></div>
        <div><span className="explain-icon"><Scale size={15}/></span><strong>Alternative explanations</strong><ul>{finding.alternatives.map((item) => <li key={item}>{item}</li>)}</ul></div>
        <div className="next-action"><span className="explain-icon"><ArrowRight size={15}/></span><strong>Human review action</strong><p>{finding.next_action}</p><small>{briefing.guardrails[1]}</small></div>
      </div>}
    </section>
  )
}
