import { useEffect, useRef } from 'react'
import { Bell, ChevronDown, Command, Menu, Moon, Search, Sun } from 'lucide-react'
import type { GraphNode, InvestigationWorkspace } from '../types'

interface Props {
  theme: 'dark' | 'light'
  onTheme: () => void
  nodes: GraphNode[]
  onSelectNode: (node: GraphNode) => void
  onMenu: () => void
  onNotifications: () => void
  workspace: InvestigationWorkspace | null
  onInvestigationChange: (id: string) => Promise<void>
}

export function Topbar({ theme, onTheme, nodes, onSelectNode, onMenu, onNotifications, workspace, onInvestigationChange }: Props) {
  const searchRef = useRef<HTMLInputElement>(null)
  useEffect(() => {
    const focusSearch = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        searchRef.current?.focus()
      }
      if (event.key === 'Escape' && document.activeElement === searchRef.current) searchRef.current?.blur()
    }
    window.addEventListener('keydown', focusSearch)
    return () => window.removeEventListener('keydown', focusSearch)
  }, [])
  return (
    <header className="topbar">
      <button className="mobile-menu icon-button" onClick={onMenu} aria-label="Open menu"><Menu size={19} /></button>
      <div className="case-switcher">
        <span>Active investigation</span>
        <div className="investigation-select"><select aria-label="Active investigation" value={workspace?.active_id ?? 'city-shield'} onChange={(event) => void onInvestigationChange(event.target.value)}>{workspace?.items.map((item) => <option value={item.id} key={item.id}>{item.name.toUpperCase()}</option>) ?? <option value="city-shield">OPERATION CITY SHIELD</option>}</select><ChevronDown size={14} /></div>
      </div>
      <div className="global-search">
        <Search size={17} />
        <input
          ref={searchRef}
          list="entity-search"
          aria-label="Search entities, relationships or evidence"
          placeholder="Search entities, relationships or evidence…"
          onChange={(event) => {
            const node = nodes.find((item) => item.name.toLowerCase() === event.target.value.toLowerCase())
            if (node) onSelectNode(node)
          }}
        />
        <datalist id="entity-search">{nodes.map((node) => <option value={node.name} key={node.id} />)}</datalist>
        <kbd><Command size={11} /> K</kbd>
      </div>
      <div className="top-actions">
        <div className="sync-state" title="Local-first analysis with optional online verification"><i /> HYBRID</div>
        <button className="icon-button" onClick={onTheme} aria-label="Toggle theme">
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <button className="icon-button notification-button" onClick={onNotifications} aria-label="Open alert center"><Bell size={18} /><i /></button>
      </div>
    </header>
  )
}
