import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { alerts as initialAlerts, graphData as fallbackGraph } from './data/mockData'
import { api, ApiError } from './api'
import type { AlertItem, AuthUser, GraphData, GraphNode, InvestigationWorkspace } from './types'
import { Sidebar, type Section } from './components/Sidebar'
import { Topbar } from './components/Topbar'
import { Dashboard } from './components/Dashboard'
import { EntityDrawer } from './components/EntityDrawer'
import { TimelinePanel } from './components/TimelinePanel'
import { MapPanel } from './components/MapPanel'
import { LoginPage } from './components/LoginPage'
import { InvestigationContextBar } from './components/InvestigationContextBar'
import { CHUNK_RETRY_KEY, ModuleErrorBoundary } from './components/ModuleErrorBoundary'

const UploadPage = lazy(() => import('./components/UploadPage').then((module) => ({ default: module.UploadPage })))
const AnalyticsPage = lazy(() => import('./components/AnalyticsPage').then((module) => ({ default: module.AnalyticsPage })))
const AlertsPage = lazy(() => import('./components/AlertsPage').then((module) => ({ default: module.AlertsPage })))
const ReportsPage = lazy(() => import('./components/ReportsPage').then((module) => ({ default: module.ReportsPage })))
const SettingsPage = lazy(() => import('./components/SettingsPage').then((module) => ({ default: module.SettingsPage })))
const NetworkGraph = lazy(() => import('./components/NetworkGraph').then((module) => ({ default: module.NetworkGraph })))
const TraceLab = lazy(() => import('./components/TraceLab').then((module) => ({ default: module.TraceLab })))
const FusionRoom = lazy(() => import('./components/FusionRoom').then((module) => ({ default: module.FusionRoom })))

const sectionFromUrl = (): Section => {
  const requested = new URLSearchParams(window.location.search).get('section')
  const allowed: Section[] = ['dashboard', 'upload', 'fusion', 'graph', 'timeline', 'map', 'analytics', 'trace', 'alerts', 'reports', 'settings']
  return allowed.includes(requested as Section) ? requested as Section : 'dashboard'
}

function App() {
  const [section, setSection] = useState<Section>(sectionFromUrl)
  const [collapsed, setCollapsed] = useState(() => window.innerWidth < 800)
  const [theme, setTheme] = useState<'dark' | 'light'>(() => (localStorage.getItem('sentinel-theme') as 'dark'|'light') || 'dark')
  const [graph, setGraph] = useState<GraphData>(fallbackGraph)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [alerts, setAlerts] = useState<AlertItem[]>(initialAlerts)
  const [workspace, setWorkspace] = useState<InvestigationWorkspace | null>(null)
  const [user, setUser] = useState<AuthUser | null>(null)
  const [authRequired, setAuthRequired] = useState(false)
  const [authChecked, setAuthChecked] = useState(false)

  useEffect(() => {
    void api.getCurrentUser()
      .then((current) => setUser(current))
      .catch((error) => {
        if (error instanceof ApiError && error.status === 401) setAuthRequired(true)
        else setUser({ email: 'offline@sentinel.local', role: 'demo', mode: 'offline-fallback' })
      })
      .finally(() => setAuthChecked(true))
  }, [])

  const refreshInvestigation = useCallback(async () => {
    const [nextGraph, nextAlerts, nextWorkspace] = await Promise.all([
      api.getGraph(),
      api.getAlerts().catch(() => initialAlerts),
      api.getInvestigations().catch(() => null),
    ])
    setGraph(nextGraph)
    setAlerts(nextAlerts)
    if (nextWorkspace) setWorkspace(nextWorkspace)
    setSelectedNode(null)
  }, [])
  useEffect(() => { if (authChecked && !authRequired) void refreshInvestigation() }, [authChecked, authRequired, refreshInvestigation])
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('sentinel-theme', theme)
  }, [theme])
  useEffect(() => {
    if (!authChecked) return
    const recoveryReset = window.setTimeout(() => sessionStorage.removeItem(CHUNK_RETRY_KEY), 5000)
    return () => window.clearTimeout(recoveryReset)
  }, [authChecked])
  useEffect(() => {
    const syncFromHistory = () => setSection(sectionFromUrl())
    window.addEventListener('popstate', syncFromHistory)
    return () => window.removeEventListener('popstate', syncFromHistory)
  }, [])

  const navigate = (next: Section) => {
    setSection(next)
    const url = new URL(window.location.href)
    if (next === 'dashboard') url.searchParams.delete('section'); else url.searchParams.set('section', next)
    if (next !== 'fusion') url.searchParams.delete('stage')
    window.history.pushState({}, '', url)
    if (window.innerWidth < 800) setCollapsed(true)
  }

  const content = (() => {
    switch (section) {
      case 'upload': return <UploadPage onInvestigationActivated={refreshInvestigation} />
      case 'fusion': return <FusionRoom activeId={workspace?.active_id} onActivate={async (id) => { await api.activateInvestigation(id); await refreshInvestigation() }} onOpenTrace={() => navigate('trace')} />
      case 'graph': return <div className="standard-page graph-page"><div className="page-heading"><div><span className="eyebrow">RELATIONSHIP INTELLIGENCE</span><h1>Knowledge graph explorer</h1><p>Explore connections, isolate communities, and uncover hidden structure.</p></div></div><NetworkGraph data={graph} selected={selectedNode} onSelect={setSelectedNode} tall /></div>
      case 'timeline': return <div className="standard-page"><div className="page-heading"><div><span className="eyebrow">TEMPORAL INTELLIGENCE</span><h1>Investigation timeline</h1><p>Correlate entities, evidence, and risk signals across time.</p></div></div><TimelinePanel full version={workspace?.active_id} /></div>
      case 'map': return <div className="standard-page"><div className="page-heading"><div><span className="eyebrow">GEOSPATIAL INTELLIGENCE</span><h1>Operational geography</h1><p>Trace incident concentrations, repeat locations, and operational-area exposure.</p></div></div><MapPanel full version={workspace?.active_id} /></div>
      case 'analytics': return <AnalyticsPage graph={graph} investigationId={workspace?.active_id} />
      case 'trace': return <TraceLab graph={graph} investigationId={workspace?.active_id} onSelect={setSelectedNode} />
      case 'alerts': return <AlertsPage initialAlerts={alerts} nodes={graph.nodes} onAlertsChange={setAlerts} onAcknowledge={async (id) => { await api.acknowledgeAlert(id); setAlerts((items) => items.map((item) => item.id === id ? { ...item, acknowledged: true } : item)) }} onSelectNode={setSelectedNode} />
      case 'reports': return <ReportsPage investigationName={workspace?.items.find((item) => item.id === workspace.active_id)?.name} />
      case 'settings': return <SettingsPage theme={theme} onTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')} user={user} onSignOut={() => { api.logout(); setAuthRequired(true); setUser(null) }} />
      default: {
        const active = workspace?.items.find((item) => item.id === workspace.active_id)
        return <Dashboard graph={graph} alerts={alerts} selected={selectedNode} onSelect={setSelectedNode} investigationId={active?.id} investigationName={active?.name} investigationSource={active?.source} sourceRecords={active?.records} />
      }
    }
  })()

  if (!authChecked) return <div className="page-loader full-screen"><span />Verifying workspace security…</div>
  if (authRequired) return <LoginPage onAuthenticated={(authenticated) => { setUser(authenticated); setAuthRequired(false); void refreshInvestigation() }} />

  const activeInvestigation = workspace?.items.find((item) => item.id === workspace.active_id)
  const openAlerts = alerts.filter((alert) => !alert.acknowledged).length

  return (
    <div className={`app-shell ${collapsed ? 'sidebar-is-collapsed' : ''}`}>
      <a className="skip-link" href="#main-intelligence">Skip to investigation content</a>
      <Sidebar section={section} onChange={navigate} collapsed={collapsed} onCollapse={() => setCollapsed(!collapsed)} alertCount={openAlerts} user={user} />
      <Topbar theme={theme} onTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')} nodes={graph.nodes} onSelectNode={setSelectedNode} onMenu={() => setCollapsed(!collapsed)} onNotifications={() => navigate('alerts')} workspace={workspace} onInvestigationChange={async (id) => { await api.activateInvestigation(id); await refreshInvestigation() }} />
      <main className="main-content" id="main-intelligence">
        <InvestigationContextBar activeCase={activeInvestigation?.name ?? 'Operation City Shield'} section={section} openAlerts={openAlerts} onNavigate={navigate}/>
        <ModuleErrorBoundary key={section} onHome={() => navigate('dashboard')}><Suspense fallback={<div className="page-loader"><span />Loading intelligence module…</div>}>{content}</Suspense></ModuleErrorBoundary>
      </main>
      <EntityDrawer node={selectedNode} graph={graph} onClose={() => setSelectedNode(null)} />
      {selectedNode && <button className="drawer-scrim" onClick={() => setSelectedNode(null)} aria-label="Close entity profile" />}
    </div>
  )
}

export default App
