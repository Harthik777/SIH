import { ArrowRight, Check, ShieldCheck } from 'lucide-react'
import type { Section } from './Sidebar'

interface Props {
  activeCase: string
  section: Section
  openAlerts: number
  onNavigate: (section: Section) => void
}

const stages = [
  { label: 'Ingest', sections: ['upload'] as Section[] },
  { label: 'Fuse', sections: ['fusion'] as Section[] },
  { label: 'Investigate', sections: ['dashboard', 'graph', 'timeline', 'map', 'analytics'] as Section[] },
  { label: 'Verify', sections: ['trace', 'alerts'] as Section[] },
  { label: 'Report', sections: ['reports'] as Section[] },
]

const nextActions: Record<Section, { label: string; button: string; target: Section }> = {
  dashboard: { label: 'Replay the strongest cross-source finding', button: 'Open fusion proof', target: 'fusion' },
  upload: { label: 'Fuse the activated evidence graph', button: 'Open fusion', target: 'fusion' },
  fusion: { label: 'Verify the strongest connection path', button: 'Trace evidence', target: 'trace' },
  graph: { label: 'Challenge a connection with stored evidence', button: 'Trace evidence', target: 'trace' },
  timeline: { label: 'Verify the entities behind the temporal signal', button: 'Trace evidence', target: 'trace' },
  map: { label: 'Verify the entities behind the location cluster', button: 'Trace evidence', target: 'trace' },
  analytics: { label: 'Validate a ranked lead before acting', button: 'Trace evidence', target: 'trace' },
  trace: { label: 'Package verified findings for human review', button: 'Prepare report', target: 'reports' },
  alerts: { label: 'Trace the evidence before acknowledging', button: 'Trace alert', target: 'trace' },
  reports: { label: 'Return to the evidence-backed case summary', button: 'Command center', target: 'dashboard' },
  settings: { label: 'Return to the active investigation', button: 'Command center', target: 'dashboard' },
}

export function InvestigationContextBar({ activeCase, section, openAlerts, onNavigate }: Props) {
  const activeStage = stages.findIndex((stage) => stage.sections.includes(section))
  const next = nextActions[section]
  return (
    <aside className="investigation-context" aria-label="Active investigation workflow">
      <div className="context-case"><ShieldCheck size={19}/><span><small>ACTIVE CASE</small><strong>{activeCase}</strong></span></div>
      <ol className="workflow-progress" aria-label="Investigation stages">
        {stages.map((stage, index) => <li className={index === activeStage ? 'active' : index < activeStage ? 'complete' : ''} key={stage.label}><i>{index < activeStage ? <Check size={11}/> : index + 1}</i><span>{stage.label}</span></li>)}
      </ol>
      <div className="context-next">
        <span><small>NEXT BEST ACTION{openAlerts ? ` · ${openAlerts} OPEN SIGNAL${openAlerts === 1 ? '' : 'S'}` : ''}</small><strong>{next.label}</strong></span>
        <button className="context-action" onClick={() => onNavigate(next.target)}>{next.button}<ArrowRight size={15}/></button>
      </div>
    </aside>
  )
}
