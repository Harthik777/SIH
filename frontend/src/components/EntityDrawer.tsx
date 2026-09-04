import { AlertTriangle, ArrowDownLeft, ArrowUpRight, Bookmark, Clock3, ExternalLink, Flag, MapPin, Network, Tag, X } from 'lucide-react'
import type { GraphData, GraphNode } from '../types'

interface Props {
  node: GraphNode | null
  graph: GraphData
  onClose: () => void
}

export function EntityDrawer({ node, graph, onClose }: Props) {
  if (!node) return null
  const edges = graph.edges.filter((edge) => edge.source === node.id || edge.target === node.id)
  return (
    <aside className="entity-drawer">
      <div className="drawer-head">
        <span className={`entity-symbol ${node.type}`}>{node.name.slice(0, 2).toUpperCase()}</span>
        <div><span className="eyebrow">{node.type} · ENTITY PROFILE</span><h2>{node.name}</h2></div>
        <button className="icon-button" onClick={onClose} aria-label="Close entity profile"><X size={18} /></button>
      </div>
      <div className="drawer-actions">
        <button><Flag size={14} /> Flag</button><button><Bookmark size={14} /> Save</button><button><ExternalLink size={14} /> Open dossier</button>
      </div>
      <div className="risk-card">
        <div className="risk-ring" style={{ '--risk': `${node.risk * 3.6}deg` } as React.CSSProperties}><span>{node.risk}</span></div>
        <div><small>COMPOSITE RISK</small><strong>{node.risk >= 80 ? 'Critical exposure' : node.risk >= 60 ? 'Elevated exposure' : 'Monitored'}</strong><p>Confidence {node.confidence}% · Updated 4m ago</p></div>
      </div>
      <div className="drawer-section">
        <h3>Intelligence summary</h3>
        <p>{node.description ?? `${node.name} is connected to ${edges.length} entities across the active investigation.`}</p>
      </div>
      <div className="property-grid">
        <div><MapPin size={14} /><span>Location<small>{node.location ?? 'Unknown'}</small></span></div>
        <div><Clock3 size={14} /><span>Last observed<small>{node.lastSeen ?? 'Not available'}</small></span></div>
        <div><Network size={14} /><span>Connections<small>{edges.length} direct links</small></span></div>
        <div><AlertTriangle size={14} /><span>Risk signals<small>{Math.max(1, Math.round(node.risk / 18))} detected</small></span></div>
      </div>
      {node.aliases && <div className="drawer-section"><h3>Known aliases</h3><div className="tag-row">{node.aliases.map((tag) => <span key={tag}><Tag size={11} />{tag}</span>)}</div></div>}
      <div className="drawer-section">
        <h3>Direct relationships <em>{edges.length}</em></h3>
        <div className="relationship-list">
          {edges.slice(0, 5).map((edge) => {
            const outgoing = edge.source === node.id
            const other = graph.nodes.find((item) => item.id === (outgoing ? edge.target : edge.source))
            return <div key={edge.id}>{outgoing ? <ArrowUpRight size={14} /> : <ArrowDownLeft size={14} />}<span><strong>{edge.label.replace(/_/g, ' ')}</strong><small>{other?.name}</small></span><em>{edge.confidence}%</em></div>
          })}
        </div>
      </div>
      <div className="drawer-note"><textarea placeholder="Add an analyst note…" /><button>Add note</button></div>
    </aside>
  )
}
