import { Braces, CalendarRange, CheckCircle2, Download, FileSpreadsheet, FileText, Globe2, Network, ShieldCheck, Sparkles } from 'lucide-react'
import { api } from '../api'

const formats = [
  { title: 'Investigation report', description: 'Executive summary, findings, evidence, and visualizations.', format: 'PDF', icon: FileText, href: '/api/export/report/pdf' },
  { title: 'Knowledge graph', description: 'All visible nodes, relationships, and entity metadata.', format: 'JSON', icon: Braces, href: api.exportUrl('json') },
  { title: 'Graph exchange', description: 'Interoperable graph structure for Gephi and network tools.', format: 'GRAPHML', icon: Network, href: api.exportUrl('graphml') },
  { title: 'Risk assessment', description: 'Entity-level scores, factors, confidence, and disposition.', format: 'CSV', icon: FileSpreadsheet, href: '/api/export/data/csv' },
  { title: 'Geospatial evidence', description: 'Operational-area concentration with proxy coordinates explicitly labelled.', format: 'GEOJSON', icon: Globe2, href: '/api/export/geojson' },
  { title: 'Timeline archive', description: 'Chronological event and relationship activity log.', format: 'CSV', icon: CalendarRange, href: '/api/export/data/csv?dataset=timeline' },
]

export function ReportsPage({ investigationName = 'Active Investigation' }: { investigationName?: string }) {
  return (
    <div className="standard-page">
      <div className="page-heading"><div><span className="eyebrow">CASE OUTPUTS</span><h1>Reports & exports</h1><p>Package verified intelligence for review, collaboration, or downstream analysis.</p></div><span className="secure-pill"><ShieldCheck size={14}/> Active investigation only</span></div>
      <section className="panel report-builder">
        <div className="report-visual"><div className="report-sheet"><span>SENTINEL / INTELLIGENCE BRIEF</span><h3>{investigationName}</h3><p>Connected crime pattern assessment</p><div className="fake-chart"><i/><i/><i/><i/><i/><i/></div><div className="fake-lines"><i/><i/><i/><i/></div></div><Sparkles size={20}/></div>
        <div className="report-copy"><span className="eyebrow"><Sparkles size={11}/> EVIDENCE-BACKED REPORTING</span><h2>Generate an investigator-ready brief</h2><p>Sentinel compiles the active graph, top risk entities, quality checks, provenance status, and required human verification steps into a structured report.</p><ul><li><CheckCircle2 size={14}/> Source-derived executive assessment</li><li><CheckCircle2 size={14}/> Evidence integrity and model status</li><li><CheckCircle2 size={14}/> Explicit analyst verification checklist</li></ul><div><button className="primary-button" onClick={()=>window.open('/api/export/report/pdf','_blank')}><FileText size={15}/> Generate report</button></div></div>
      </section>
      <div className="section-heading"><div><span className="eyebrow">STRUCTURED DATA</span><h2>Export investigation</h2></div><small>Exports are generated from the complete active investigation.</small></div>
      <div className="export-grid">{formats.map(({title,description,format,icon:Icon,href})=><article className="panel export-card" key={title}><span><Icon size={20}/></span><div><h3>{title}</h3><p>{description}</p></div><a href={href} download><em>{format}</em><Download size={15}/></a></article>)}</div>
      <section className="panel report-history"><div className="panel-header"><div><span className="eyebrow">AUDITABLE GENERATION</span><h2>No fabricated document history</h2></div><span className="source-label">ON DEMAND</span></div><div className="report-history-note"><ShieldCheck size={19}/><div><strong>Exports are created only when requested</strong><p>The API streams a fresh artifact from the active evidence graph; Sentinel does not display placeholder report records.</p></div></div></section>
    </div>
  )
}
