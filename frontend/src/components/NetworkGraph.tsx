import { useEffect, useMemo, useRef, useState } from 'react'
import cytoscape, { type Core } from 'cytoscape'
import { Focus, Maximize2, RotateCcw, Search, SlidersHorizontal, ZoomIn, ZoomOut } from 'lucide-react'
import type { EntityType, GraphData, GraphNode } from '../types'

const colors: Record<EntityType, string> = {
  person: '#9b8cff',
  organization: '#45d6b1',
  location: '#5ca9ff',
  account: '#f6b85b',
  phone: '#58d3e7',
  event: '#ef6f84',
  vehicle: '#f18ec7',
  crime: '#ff8a65',
}

type LayoutName = 'cose' | 'circle' | 'breadthfirst'

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
  const [filters, setFilters] = useState<Set<EntityType>>(new Set(['person', 'organization', 'location', 'account', 'event', 'vehicle', 'crime']))
  const [showFilters, setShowFilters] = useState(false)
  const [query, setQuery] = useState('')
  const [themeKey, setThemeKey] = useState(document.documentElement.dataset.theme)

  const visibleData = useMemo(() => {
    const matching = data.nodes.filter((node) => filters.has(node.type) && node.name.toLowerCase().includes(query.toLowerCase()))
    const nodeLimit = tall ? 900 : 260
    let nodes = matching
    if (matching.length > nodeLimit && !query) {
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
    return { nodes, edges: data.edges.filter((edge) => visible.has(edge.source) && visible.has(edge.target)) }
  }, [data, filters, query, tall])

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
        ...visibleData.nodes.map((node) => ({ data: { ...node, label: node.name, color: colors[node.type], size: 25 + node.risk * .16 } })),
        ...visibleData.edges.map((edge) => ({ data: edge, classes: edge.anomalous ? 'anomalous' : '' })),
      ],
      style: [
        { selector: 'node', style: {
          'background-color': 'data(color)', 'border-color': 'data(color)', 'border-width': 2, 'border-opacity': .38,
          width: 'data(size)', height: 'data(size)', label: 'data(label)', color: textMuted,
          'font-family': 'Inter, sans-serif', 'font-size': 7.5, 'text-valign': 'bottom', 'text-margin-y': 6,
          'text-outline-color': labelBackground, 'text-outline-width': 2, 'overlay-opacity': 0,
        } },
        { selector: 'edge', style: {
          width: 1, 'line-color': graphEdge, 'target-arrow-color': graphEdge, 'target-arrow-shape': 'triangle',
          'curve-style': 'bezier', label: 'data(label)', color: textFaint, 'font-size': 5.5,
          'text-background-color': labelBackground, 'text-background-opacity': .8, 'text-background-padding': '2px',
        } },
        { selector: 'edge.anomalous', style: { width: 1.8, 'line-color': '#ef6f84', 'target-arrow-color': '#ef6f84', 'line-style': 'dashed' } },
        { selector: 'node:selected', style: { 'border-width': 5, 'border-opacity': .18, 'border-color': '#ffffff' } },
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
          <Search size={14} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find in graph" />
          <button onClick={() => setShowFilters((value) => !value)} className={showFilters ? 'active' : ''}><SlidersHorizontal size={14} /></button>
        </div>
        {showFilters && (
          <div className="graph-filter-popover">
            <strong>Entity types</strong>
            {(Object.keys(colors) as EntityType[]).map((type) => (
              <label key={type}><input type="checkbox" checked={filters.has(type)} onChange={() => toggleType(type)} /><i style={{ background: colors[type] }} />{type}</label>
            ))}
          </div>
        )}
        <div className="graph-legend">
          {(Object.entries(colors) as [EntityType, string][]).map(([type, color]) => <span key={type}><i style={{ background: color }} />{type}</span>)}
          <span><i className="anomaly-line" />Anomalous link</span>
        </div>
      </div>
    </section>
  )
}
