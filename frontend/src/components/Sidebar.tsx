import {
  Activity, Bell, BrainCircuit, ChevronLeft, Database, FileDown, Fingerprint, Layers3, LayoutDashboard,
  MapPinned, Network, Settings, ShieldCheck, UploadCloud,
} from 'lucide-react'
import type { AuthUser } from '../types'
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
  user: AuthUser | null
}

const sessionProfile = (user: AuthUser | null) => {
  if (!user) return { initials: '--', name: 'Session unavailable', role: 'Identity unavailable' }
  if (user.mode === 'synthetic-public-demo') return { initials: 'PD', name: 'Public demo', role: 'Synthetic showcase' }
  if (user.mode === 'offline-fallback') return { initials: 'OF', name: 'Offline workspace', role: 'Local fallback' }

  const words = user.email.split('@')[0].split(/[._-]+/).filter(Boolean)
  const name = words.map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ') || user.email
  const initials = (words.length > 1 ? words.map((word) => word[0]).join('') : words[0]?.slice(0, 2) || 'ID').slice(0, 2).toUpperCase()
  const role = user.role === 'demo' ? 'Demonstration role' : user.role.charAt(0).toUpperCase() + user.role.slice(1)
  return { initials, name, role }
}

export function Sidebar({ section, onChange, collapsed, onCollapse, alertCount, user }: Props) {
  const profile = sessionProfile(user)
  const renderItem = ({ id, label, icon: Icon }: (typeof primary)[number]) => (
    <button
      key={id}
      className={`nav-item ${section === id ? 'active' : ''}`}
      onClick={() => onChange(id)}
      title={collapsed ? label : undefined}
      aria-current={section === id ? 'page' : undefined}
    >
      <Icon size={18} strokeWidth={1.8} />
      {!collapsed && <span>{label}</span>}
      {!collapsed && id === 'alerts' && alertCount > 0 && <em>{alertCount}</em>}
    </button>
  )

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-brand"><Logo compact={collapsed} /></div>
      <nav aria-label="Sentinel workspace">
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
        <button className={`nav-item ${section === 'settings' ? 'active' : ''}`} aria-label={collapsed ? 'Settings' : undefined} title={collapsed ? 'Settings' : undefined} aria-current={section === 'settings' ? 'page' : undefined} onClick={() => onChange('settings')}>
          <Settings size={18} strokeWidth={1.8} />
          {!collapsed && <span>Settings</span>}
        </button>
        {!collapsed && (
          <div className="analyst" title={user?.email}>
            <div className="avatar">{profile.initials}</div>
            <div><strong>{profile.name}</strong><small><ShieldCheck size={12} /> {profile.role}</small></div>
          </div>
        )}
      </div>
      <button className="collapse-btn" onClick={onCollapse} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}><ChevronLeft size={15} /></button>
    </aside>
  )
}
