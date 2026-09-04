import { BrainCircuit, Database, Fingerprint, Scale, ShieldCheck } from 'lucide-react'
import type { InvestigationBriefing } from '../types'

export function TrustPanel({ briefing }: { briefing: InvestigationBriefing | null }) {
  const quality = briefing?.quality
  const modelReady = briefing?.model.status === 'ready'
  return (
    <section className="panel trust-panel">
      <div className="panel-header"><div><span className="eyebrow">ASSURANCE LAYER</span><h2>Evidence trust center</h2></div><span className="trust-mode"><i/> ZERO-CLOUD MODE</span></div>
      <div className="trust-grid">
        <div><span><Database size={16}/></span><small>DATA QUALITY</small><strong>{quality?.quality_gate.toUpperCase() ?? 'CHECKING'}</strong><em>{quality?.required_field_completeness ?? 0}% required fields</em></div>
        <div><span><Fingerprint size={16}/></span><small>CHAIN OF CUSTODY</small><strong>{briefing ? `${briefing.provenance.verified}/${briefing.provenance.total}` : '—'}</strong><em>SHA-256 verified sources</em></div>
        <div><span><BrainCircuit size={16}/></span><small>GRAPHSAGE</small><strong>{modelReady ? 'REPRODUCED' : 'REVIEW'}</strong><em>{modelReady ? 'field accuracy not established' : 'fallback mode active'}</em></div>
        <div><span><Scale size={16}/></span><small>DECISION POLICY</small><strong>HUMAN</strong><em>no automated enforcement</em></div>
      </div>
      <div className="trust-footer"><span><ShieldCheck size={12}/> W3C PROV-O aligned</span><span>{quality?.unique_case_numbers ?? 0} unique source IDs · {quality?.duplicate_case_numbers ?? 0} duplicates · {quality?.ontology_mapping_coverage ?? 0}% ontology mapped</span></div>
    </section>
  )
}
