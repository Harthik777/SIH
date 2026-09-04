import { useEffect, useMemo, useRef, useState } from 'react'
import cytoscape, { type Core } from 'cytoscape'
import { Focus, Maximize2, RotateCcw, Search, SlidersHorizontal, ZoomIn, ZoomOut } from 'lucide-react'
import type { EntityType, GraphData, GraphNode } from '../types'

const colors: Record<EntityType, string> = {
  person: '#9b8cff',
  protected_person: '#7ee7c6',
  organization: '#45d6b1',
  location: '#5ca9ff',
  account: '#f6b85b',
  phone: '#58d3e7',
  event: '#ef6f84',
  vehicle: '#f18ec7',
  crime: '#ff8a65',
}

type LayoutName = 'cose' | 'circle' | 'breadthfirst'
type GraphScope = 'focus' | 'all'

interface Props {
  data: GraphData
  selected?: GraphNode | null
  onSelect: (node: GraphNode) => void
  expanded?: boolean
  onExpand?: () => void
  tall?: boolean
}

export function NetworkGraph({ data, selected, onSelect, expanded, onExpand, tall }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)
  const [layout, setLayout] = useState<LayoutName>('cose')
  const [filters, setFilters] = useState<Set<EntityType>>(new Set(['person', 'protected_person', 'organization', 'location', 'account', 'phone', 'event', 'vehicle', 'crime']))
  const [showFilters, setShowFilters] = useState(false)
  const [query, setQuery] = useState('')
  const [scope, setScope] = useState<GraphScope>('focus')
  const [themeKey, setThemeKey] = useState(document.documentElement.dataset.theme)

  const visibleData = useMemo(() => {
    const eligibleNodes = data.nodes.filter((node) => filters.has(node.type))
    const eligibleIds = new Set(eligibleNodes.map((node) => node.id))
    const eligibleEdges = data.edges.filter((edge) => eligibleIds.has(edge.source) && eligibleIds.has(edge.target))
    const degree = new Map<string, number>()
    eligibleEdges.forEach((edge) => {
      degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1)
      degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1)
    })
    const normalizedQuery = query.trim().toLowerCase()
    const queryMatches = normalizedQuery ? eligibleNodes.filter((node) => node.name.toLowerCase().includes(normalizedQuery)) : []
    const defaultFocus = [...eligibleNodes]
      .filter((node) => node.type !== 'protected_person')
      .sort((a, b) => b.risk - a.risk || (degree.get(b.id) ?? 0) - (degree.get(a.id) ?? 0) || a.name.localeCompare(b.name))[0]
    const focusNode = selected && eligibleIds.has(selected.id) ? selected : defaultFocus
    const selectedIds = new Set<string>()
    const focusLimit = tall ? 80 : 38

    if (normalizedQuery) {
      queryMatches.forEach((node) => selectedIds.add(node.id))
      const seeds = new Set(selectedIds)
      for (const edge of eligibleEdges) {
        if (selectedIds.size >= focusLimit) break
        if (seeds.has(edge.source)) selectedIds.add(edge.target)
        if (seeds.has(edge.target)) selectedIds.add(edge.source)
      }
    } else if (scope === 'focus' && focusNode) {
      selectedIds.add(focusNode.id)
      let frontier = new Set([focusNode.id])
      for (let depth = 0; depth < 2 && frontier.size && selectedIds.size < focusLimit; depth += 1) {
        const next = new Set<string>()
        for (const edge of eligibleEdges) {
          if (selectedIds.size >= focusLimit) break
          if (frontier.has(edge.source) && !selectedIds.has(edge.target)) { selectedIds.add(edge.target); next.add(edge.target) }
          if (frontier.has(edge.target) && !selectedIds.has(edge.source)) { selectedIds.add(edge.source); next.add(edge.source) }
        }
        frontier = next
      }
    } else {
      eligibleNodes.forEach((node) => selectedIds.add(node.id))
    }

    let matching = eligibleNodes.filter((node) => selectedIds.has(node.id))
    const nodeLimit = tall ? 900 : 260
    let nodes = matching
    if (matching.length > nodeLimit && !normalizedQuery) {
      const eligible = new Set(matching.map((node) => node.id))
      const selectedIds = new Set([...matching].sort((a, b) => b.risk - a.risk).slice(0, Math.min(80, nodeLimit)).map((node) => node.id))
      for (let pass = 0; pass < 2 && selectedIds.size < nodeLimit; pass += 1) {
        for (const edge of data.edges) {
          if (selectedIds.size >= nodeLimit) break
          if (selectedIds.has(edge.source) && eligible.has(edge.target)) selectedIds.add(edge.target)
          if (selectedIds.has(edge.target) && eligible.has(edge.source)) selectedIds.add(edge.source)
        }
      }
      for (const node of [...matching].sort((a, b) => b.risk - a.risk)) {
        if (selectedIds.size >= nodeLimit) break
        selectedIds.add(node.id)
      }
      nodes = matching.filter((node) => selectedIds.has(node.id))
    }
    const visible = new Set(nodes.map((node) => node.id))
    const edges = eligibleEdges.filter((edge) => visible.has(edge.source) && visible.has(edge.target))
    return { nodes, edges, focusId: focusNode?.id, focusName: focusNode?.name, queryMatches: new Set(queryMatches.map((node) => node.id)) }
  }, [data, filters, query, scope, selected, tall])

  useEffect(() => {
    const observer = new MutationObserver(() => setThemeKey(document.documentElement.dataset.theme))
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!containerRef.current) return
    cyRef.current?.destroy()
    const rootStyle = getComputedStyle(document.documentElement)
    const token = (name: string, fallback: string) => rootStyle.getPropertyValue(name).trim() || fallback
    const textMuted = token('--text-muted', '#9baea7')
    const textFaint = token('--text-faint', '#657a73')
    const graphEdge = token('--graph-edge', 'rgba(127,174,160,.33)')
    const labelBackground = token('--graph-label-bg', '#0d1916')
    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...visibleData.nodes.map((node) => ({
          data: {
            ...node,
            displayLabel: node.id === visibleData.focusId || node.type === 'person' || node.risk >= 85 || visibleData.queryMatches.has(node.id) ? node.name : '',
            color: colors[node.type],
            size: node.type === 'protected_person' ? 31 : 27 + node.risk * .16,
          },
          classes: visibleData.queryMatches.has(node.id) ? 'matched' : '',
        })),
        ...visibleData.edges.map((edge) => ({
          data: { ...edge, displayLabel: edge.anomalous || edge.source === visibleData.focusId || edge.target === visibleData.focusId ? edge.label : '' },
          classes: `${edge.anomalous ? 'anomalous ' : ''}${edge.source === visibleData.focusId || edge.target === visibleData.focusId ? 'focus-link' : ''}`.trim(),
        })),
      ],
      style: [
        { selector: 'node', style: {
          'background-color': 'data(color)', 'border-color': 'data(color)', 'border-width': 2, 'border-opacity': .38,
          width: 'data(size)', height: 'data(size)', label: 'data(displayLabel)', color: textMuted,
          'font-family': 'Inter, sans-serif', 'font-size': 11, 'font-weight': 600, 'text-valign': 'bottom', 'text-margin-y': 7,
          'text-outline-color': labelBackground, 'text-outline-width': 2, 'overlay-opacity': 0,
        } },
        { selector: 'edge', style: {
          width: 1, 'line-color': graphEdge, 'target-arrow-color': graphEdge, 'target-arrow-shape': 'triangle',
          'curve-style': 'bezier', label: 'data(displayLabel)', color: textFaint, 'font-size': 9.5,
          'text-background-color': labelBackground, 'text-background-opacity': .8, 'text-background-padding': '2px',
        } },
        { selector: 'edge.focus-link', style: { width: 2, 'line-color': '#45d6b1', 'target-arrow-color': '#45d6b1' } },
        { selector: 'edge.anomalous', style: { width: 1.8, 'line-color': '#ef6f84', 'target-arrow-color': '#ef6f84', 'line-style': 'dashed' } },
        { selector: 'node:selected', style: { 'border-width': 5, 'border-opacity': .18, 'border-color': '#ffffff' } },
        { selector: 'node.matched', style: { 'border-width': 5, 'border-opacity': .7, 'border-color': '#45d6b1' } },
        { selector: 'node[type = "protected_person"]', style: { 'border-style': 'double', 'border-width': 4, 'shape': 'diamond' } },
      ],
      layout: { name: layout, animate: false, padding: 35, nodeRepulsion: () => 9000, idealEdgeLength: () => 90 },
      minZoom: .35,
      maxZoom: 2.5,
    })
    cy.on('tap', 'node', (event) => {
      const node = data.nodes.find((item) => item.id === event.target.id())
      if (node) onSelect(node)
    })
    cyRef.current = cy
    const resize = new ResizeObserver(() => { cy.resize(); cy.fit(undefined, 30) })
    resize.observe(containerRef.current)
    return () => { resize.disconnect(); cy.destroy() }
  }, [visibleData, layout, data.nodes, onSelect, themeKey])

  useEffect(() => {
    if (!selected || !cyRef.current) return
    const node = cyRef.current.getElementById(selected.id)
    if (node.nonempty()) {
      cyRef.current.elements().unselect()
      node.select()
      cyRef.current.animate({ center: { eles: node }, zoom: 1.35 }, { duration: 350 })
    }
  }, [selected])

  const toggleType = (type: EntityType) => setFilters((current) => {
    const next = new Set(current)
    if (next.has(type)) next.delete(type); else next.add(type)
    return next
  })

  return (
    <section className={`panel graph-panel ${expanded ? 'expanded' : ''} ${tall ? 'tall' : ''}`}>
      <div className="panel-header">
        <div><span className="eyebrow">ENTITY NETWORK</span><h2>Knowledge graph</h2></div>
        <div className="graph-head-actions">
          <span className="graph-count">{visibleData.nodes.length.toLocaleString()}{visibleData.nodes.length < data.nodes.length ? ` / ${data.nodes.length.toLocaleString()}` : ''} entities <i /> {visibleData.edges.length.toLocaleString()} links</span>
          <button className={`graph-scope-button ${scope === 'focus' ? 'active' : ''}`} aria-pressed={scope === 'focus'} onClick={() => setScope((value) => value === 'focus' ? 'all' : 'focus')}><Focus size={14}/>{scope === 'focus' ? 'Focused view' : 'All entities'}</button>
          <select aria-label="Graph layout" value={layout} onChange={(event) => setLayout(event.target.value as LayoutName)}>
            <option value="cose">Force layout</option><option value="circle">Circular</option><option value="breadthfirst">Hierarchical</option>
          </select>
          {onExpand && <button className="icon-button small" onClick={onExpand} aria-label="Expand graph"><Maximize2 size={15} /></button>}
        </div>
      </div>
      <div className="graph-stage">
        <div ref={containerRef} className="cy-container" />
        <div className="graph-toolbar">
          <button onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)} aria-label="Zoom in"><ZoomIn size={15} /></button>
          <button onClick={() => cyRef.current?.zoom(cyRef.current.zoom() / 1.2)} aria-label="Zoom out"><ZoomOut size={15} /></button>
          <button onClick={() => cyRef.current?.fit(undefined, 30)} aria-label="Fit graph"><Focus size={15} /></button>
          <button onClick={() => cyRef.current?.layout({ name: layout, animate: true, animationDuration: 450 }).run()} aria-label="Reset layout"><RotateCcw size={15} /></button>
        </div>
        <div className="graph-search">
          <Search size={16} /><input aria-label="Find an entity in the graph" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find an entity" />
          <button aria-label="Filter graph entity types" aria-expanded={showFilters} onClick={() => setShowFilters((value) => !value)} className={showFilters ? 'active' : ''}><SlidersHorizontal size={15} /></button>
        </div>
        {showFilters && (
          <div className="graph-filter-popover">
            <strong>Entity types</strong>
            {(Object.keys(colors) as EntityType[]).map((type) => (
              <label key={type}><input type="checkbox" checked={filters.has(type)} onChange={() => toggleType(type)} /><i style={{ background: colors[type] }} />{type}</label>
            ))}
          </div>
        )}
        {scope === 'focus' && !query && visibleData.focusName && <div className="graph-focus-note" role="status"><Focus size={13}/><span><strong>Focused on {visibleData.focusName}</strong><small>Two-hop evidence neighbourhood · select a node to refocus</small></span></div>}
        {query && <div className="graph-focus-note" role="status"><Search size={13}/><span><strong>{visibleData.queryMatches.size} matching entit{visibleData.queryMatches.size === 1 ? 'y' : 'ies'}</strong><small>Showing matches with directly connected evidence</small></span></div>}
        <div className="graph-legend">
          {(Object.entries(colors) as [EntityType, string][]).map(([type, color]) => <span key={type}><i style={{ background: color }} />{type}</span>)}
          <span><i className="anomaly-line" />Anomalous link</span>
        </div>
      </div>
    </section>
  )
}
