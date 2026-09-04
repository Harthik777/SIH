import {
  Activity, Bell, BrainCircuit, ChevronLeft, Database, FileDown, Fingerprint, Layers3, LayoutDashboard,
  MapPinned, Network, Settings, ShieldCheck, UploadCloud,
} from 'lucide-react'
import { Logo } from './Logo'

export type Section = 'dashboard' | 'upload' | 'fusion' | 'graph' | 'timeline' | 'map' | 'analytics' | 'trace' | 'alerts' | 'reports' | 'settings'

const primary: { id: Section; label: string; icon: typeof Activity }[] = [
  { id: 'dashboard', label: 'Command center', icon: LayoutDashboard },
  { id: 'upload', label: 'Data ingestion', icon: UploadCloud },
  { id: 'fusion', label: 'Fusion replay', icon: Layers3 },
  { id: 'graph', label: 'Graph explorer', icon: Network },
  { id: 'timeline', label: 'Timeline', icon: Activity },
  { id: 'map', label: 'Geo intelligence', icon: MapPinned },
]

const intelligence: { id: Section; label: string; icon: typeof Activity }[] = [
  { id: 'analytics', label: 'Advanced analytics', icon: BrainCircuit },
  { id: 'trace', label: 'TRACE Lab', icon: Fingerprint },
  { id: 'alerts', label: 'Alert center', icon: Bell },
  { id: 'reports', label: 'Reports & export', icon: FileDown },
]

interface Props {
  section: Section
  onChange: (section: Section) => void
  collapsed: boolean
  onCollapse: () => void
  alertCount: number
}

export function Sidebar({ section, onChange, collapsed, onCollapse, alertCount }: Props) {
  const renderItem = ({ id, label, icon: Icon }: (typeof primary)[number]) => (
    <button
      key={id}
      className={`nav-item ${section === id ? 'active' : ''}`}
      onClick={() => onChange(id)}
      title={collapsed ? label : undefined}
    >
      <Icon size={18} strokeWidth={1.8} />
      {!collapsed && <span>{label}</span>}
      {!collapsed && id === 'alerts' && alertCount > 0 && <em>{alertCount}</em>}
    </button>
  )

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-brand"><Logo compact={collapsed} /></div>
      <nav>
        {!collapsed && <span className="nav-label">INVESTIGATE</span>}
        {primary.map(renderItem)}
        {!collapsed && <span className="nav-label intelligence-label">INTELLIGENCE</span>}
        {intelligence.map(renderItem)}
      </nav>
      <div className="sidebar-bottom">
        <div className="system-card">
          <span className="system-icon"><Database size={15} /></span>
          {!collapsed && <div><strong>Evidence verified</strong><small>Local provenance manifest</small></div>}
          {!collapsed && <i />}
        </div>
        <button className={`nav-item ${section === 'settings' ? 'active' : ''}`} onClick={() => onChange('settings')}>
          <Settings size={18} strokeWidth={1.8} />
          {!collapsed && <span>Settings</span>}
        </button>
        {!collapsed && (
          <div className="analyst">
            <div className="avatar">AK</div>
            <div><strong>Alex Kim</strong><small><ShieldCheck size={12} /> Lead analyst</small></div>
            <button aria-label="Account menu">•••</button>
          </div>
        )}
      </div>
      <button className="collapse-btn" onClick={onCollapse} aria-label="Collapse sidebar"><ChevronLeft size={15} /></button>
    </aside>
  )
}
