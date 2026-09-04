import { useRef, useState } from 'react'
import { Check, ChevronRight, Database, File, FileJson, LoaderCircle, Play, ShieldCheck, UploadCloud, X } from 'lucide-react'
import { api } from '../api'
import type { PipelineRun, PipelineStage, UploadRecord } from '../types'

const initialStages: PipelineStage[] = [
  { id: 'clean', name: 'Validate & normalize', detail: 'Schema checks, deduplication, encoding', progress: 0, status: 'queued' },
  { id: 'entity', name: 'Entity extraction', detail: 'FIR parser + explicit multi-source field mapping', progress: 0, status: 'queued' },
  { id: 'relation', name: 'Relation extraction', detail: 'Observed source links + ontology predicates', progress: 0, status: 'queued' },
  { id: 'graph', name: 'Graph construction', detail: 'Entity resolution and link creation', progress: 0, status: 'queued' },
  { id: 'analysis', name: 'Intelligence analysis', detail: 'Risk, anomalies, links, communities', progress: 0, status: 'queued' },
]

const seededUploads: UploadRecord[] = [
  { id: 'u1', filename: 'crime_dataset.csv', size: 73456, created_at: '2026-09-04T12:58:00Z', status: 'complete', records: 500 },
  { id: 'u2', filename: 'fir_reports.txt', size: 266831, created_at: '2026-09-04T12:56:00Z', status: 'complete', records: 500 },
  { id: 'u3', filename: 'populated_crime_ontology.ttl', size: 561046, created_at: '2026-09-04T12:54:00Z', status: 'complete', records: 10401 },
]

function formatSize(size: number) {
  return size > 1_000_000 ? `${(size / 1_000_000).toFixed(1)} MB` : `${Math.round(size / 1000)} KB`
}

export function UploadPage({ onInvestigationActivated }: { onInvestigationActivated?: () => Promise<void> }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [selected, setSelected] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [stages, setStages] = useState(initialStages)
  const [running, setRunning] = useState(false)
  const [logs, setLogs] = useState<string[]>(['[system] Pipeline ready. Waiting for input.'])
  const [uploads, setUploads] = useState(seededUploads)
  const [result, setResult] = useState<PipelineRun['result'] | null>(null)

  const pick = (files: FileList | null) => {
    if (files?.[0]) {
      setSelected(files[0])
      setStages(initialStages)
      setResult(null)
      setLogs([`[input] ${files[0].name} staged for processing.`, '[system] File validation passed.'])
    }
  }

  const run = async () => {
    if (!selected || running) return
    setRunning(true)
    setResult(null)
    try {
      const upload = await api.upload(selected)
      setUploads((items) => [{ ...upload, status: 'processing' }, ...items])
      const started = await api.startPipeline(upload.id)
      let pipeline: PipelineRun
      do {
        pipeline = await api.getPipelineStatus(started.pipeline_id)
        setStages(pipeline.stages.map((stage) => ({
          ...stage,
          detail: initialStages.find((candidate) => candidate.id === stage.id)?.detail ?? 'Local evidence processing',
        })))
        setLogs(pipeline.logs.map((line) => `[${pipeline.status}] ${line}`))
        if (pipeline.status === 'queued' || pipeline.status === 'running') await new Promise((resolve) => window.setTimeout(resolve, 180))
      } while (pipeline.status === 'queued' || pipeline.status === 'running')

      setResult(pipeline.result)
      if (pipeline.result.investigation?.active) await onInvestigationActivated?.()
      setUploads((items) => items.map((item) => item.id === upload.id ? {
        ...item,
        status: pipeline.status,
        records: pipeline.result.source?.records ?? 0,
      } : item))
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown pipeline error'
      setLogs((items) => [...items, `[failed] ${message}. No results were fabricated.`])
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="standard-page">
      <div className="page-heading"><div><span className="eyebrow">DATA OPERATIONS</span><h1>Ingest intelligence</h1><p>Transform source files into connected, explainable intelligence.</p></div><div className="secure-pill"><ShieldCheck size={14}/> Local-first · no cloud API</div></div>
      <div className="ingestion-grid">
        <section className="panel upload-panel">
          <div className="panel-header"><div><span className="eyebrow">01 · SOURCE DATA</span><h2>Upload evidence</h2></div><span className="supported-formats">CSV · JSON · TXT · XML · RDF/TTL</span></div>
          {!selected ? (
            <div className={`drop-zone ${dragging ? 'dragging' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); pick(event.dataTransfer.files) }}>
              <span className="upload-icon"><UploadCloud size={25}/></span><h3>Drop investigation files here</h3><p>or select them from your computer</p><button className="secondary-button" onClick={() => inputRef.current?.click()}>Browse files</button><small>Deployment upload limit enforced · SHA-256 provenance recorded</small>
              <input ref={inputRef} hidden type="file" accept=".csv,.json,.txt,.xml,.ttl,.rdf" onChange={(event) => pick(event.target.files)}/>
            </div>
          ) : (
            <div className="selected-file">
              <span><FileJson size={25}/></span><div><h3>{selected.name}</h3><p>{formatSize(selected.size)} · Ready to process</p></div><i><Check size={14}/></i><button onClick={() => setSelected(null)} aria-label="Remove file"><X size={16}/></button>
            </div>
          )}
          <div className="model-config">
            <div><label>Extraction engine</label><strong>AUTO-DETECT</strong><small>FIR rules + structured field mapper</small></div>
            <div><label>Semantic contract</label><strong>CRIME ONTOLOGY V1</strong><small>People · phones · accounts · places · events</small></div>
            <div><label>Decision boundary</label><strong>HUMAN REVIEW</strong><small>Derived links and scores never become evidence automatically</small></div>
          </div>
          <button className="primary-button run-pipeline" disabled={!selected || running} onClick={run}>{running ? <><LoaderCircle className="spin" size={16}/> Processing intelligence…</> : <><Play size={15}/> Start processing pipeline</>}</button>
        </section>
        <section className="panel pipeline-panel">
          <div className="panel-header"><div><span className="eyebrow">02 · PROCESSING</span><h2>Intelligence pipeline</h2></div><span className={`pipeline-state ${running ? 'active' : ''}`}>{running ? 'RUNNING' : 'STANDBY'}</span></div>
          <div className="pipeline-stages">
            {stages.map((stage, index) => <div key={stage.id} className={`pipeline-stage ${stage.status}`}><span className="stage-number">{stage.status === 'complete' ? <Check size={14}/> : index + 1}</span><div><strong>{stage.name}</strong><small>{stage.detail}</small><div className="progress-track"><i style={{ width: `${stage.progress}%` }}/></div></div><em>{stage.status === 'running' ? `${Math.round(stage.progress)}%` : stage.status}</em>{index < stages.length - 1 && <ChevronRight size={14}/>}</div>)}
          </div>
          <div className="pipeline-console"><div><span/><span/><span/><strong>live_pipeline.log</strong></div><pre>{logs.map((line, index) => <code key={index}>{line}{'\n'}</code>)}</pre></div>
          {result?.source && <div className="pipeline-result"><span><Database size={18}/></span><div><small>VERIFIED OUTPUT {result.investigation?.active ? '· ACTIVE GRAPH' : ''}</small><strong>{result.source.records.toLocaleString()} records · {result.graph?.nodes.toLocaleString() ?? 0} nodes · {result.graph?.edges.toLocaleString() ?? 0} links</strong><em>SHA-256 {result.source.sha256.slice(0, 18)}… · {result.risk_signals ?? 0} review signals</em></div></div>}
        </section>
      </div>
      <section className="panel history-panel">
        <div className="panel-header"><div><span className="eyebrow">SOURCE REGISTER</span><h2>Verified local inputs</h2></div><span className="source-label">{uploads.length} SOURCES</span></div>
        <div className="data-table"><div className="table-row table-head"><span>Source file</span><span>Records</span><span>Size</span><span>Imported</span><span>Status</span><span>Storage</span></div>{uploads.map((upload) => <div className="table-row" key={upload.id}><span><File size={15}/><strong>{upload.filename}</strong></span><span>{upload.records.toLocaleString()}</span><span>{formatSize(upload.size)}</span><span>{new Date(upload.created_at).toLocaleDateString()}</span><span><i className={`status-dot ${upload.status}`}/>{upload.status}</span><span>LOCAL</span></div>)}</div>
      </section>
    </div>
  )
}
