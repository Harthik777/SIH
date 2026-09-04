import { MapPin } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api'
import { mapPoints } from '../data/mockData'
import type { LocationSignal } from '../types'

export function MapPanel({ full = false, version }: { full?: boolean; version?: string }) {
  const [points, setPoints] = useState<LocationSignal[]>(mapPoints.map((point) => ({ ...point, lat: 0, lng: 0, entity_id: point.id, coordinate_basis: 'offline fallback' })))
  useEffect(() => { api.getLocations().then(setPoints).catch(() => undefined) }, [version])
  const incidentCount = points.reduce((total, point) => total + point.count, 0)
  return (
    <section className={`panel map-panel ${full ? 'page-panel' : ''}`}>
      <div className="panel-header"><div><span className="eyebrow">GEO INTELLIGENCE</span><h2>Operational concentration</h2></div><span className="source-label">NON-GPS DISPLAY GRID</span></div>
      <div className={`world-map ${full ? 'large' : ''}`}>
        <svg viewBox="0 0 900 440" preserveAspectRatio="none" aria-hidden="true">
          <path className="city-boundary" d="M244 24 641 30 701 76 684 129 727 183 700 235 722 292 670 345 629 414 299 406 276 363 284 312 252 271 268 211 234 164 254 111 231 70Z" />
          <path className="city-grid" d="M282 56 662 61M268 102 683 108M259 151 694 157M270 201 701 207M267 250 699 256M287 299 688 305M285 349 655 355M352 34 343 402M423 29 418 407M498 30 494 410M571 31 563 413M637 34 622 410" />
          <path className="city-river" d="M247 177Q365 155 448 201T698 175M473 197Q489 264 459 319" />
          <path className="map-lines" d="M432 114Q505 177 567 225M567 225Q623 275 642 334M342 259Q456 283 567 225M432 114Q383 188 342 259" />
        </svg>
        {points.map((point) => <button key={point.id} className={`map-marker ${point.risk > 80 ? 'hot' : ''}`} style={{ left: `${point.x}%`, top: `${point.y}%` }} title={`${point.name}: ${point.count} linked incidents · ${point.coordinate_basis}`}><i /><span>{point.count}</span><em>{point.name}</em></button>)}
        <div className="map-caption"><MapPin size={13}/><span><strong>{incidentCount}</strong> location links</span><i/>{points.length} location entities · display proxy, not GPS</div>
      </div>
    </section>
  )
}
