import { Clock3 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api'
import { timelineEvents } from '../data/mockData'
import type { TimelineEvent } from '../types'

export function TimelinePanel({ full = false, version }: { full?: boolean; version?: string }) {
  const [sourceEvents, setSourceEvents] = useState<TimelineEvent[]>(timelineEvents)
  useEffect(() => { api.getTimeline().then(setSourceEvents).catch(() => undefined) }, [version])
  const events = full ? sourceEvents : sourceEvents.slice(0, 3)
  const chronological = [...sourceEvents].filter((event) => event.occurred_at).sort((a, b) => String(a.occurred_at).localeCompare(String(b.occurred_at)))
  const rangeStart = chronological[0]?.date ?? 'No dates'
  const rangeEnd = chronological[chronological.length - 1]?.date ?? 'available'
  return (
    <section className={`panel timeline-panel ${full ? 'page-panel' : ''}`}>
      <div className="panel-header"><div><span className="eyebrow">EVENT CORRELATION</span><h2>Activity timeline</h2></div><span className="source-label">ACTIVE EVIDENCE · {sourceEvents.length} DATED CASES</span></div>
      {full && <div className="timeline-range"><span>{rangeStart}</span><div><i /><i /></div><span>{rangeEnd}</span></div>}
      <div className="timeline-list">
        {events.map((event, index) => (
          <article key={event.id} className={event.severity ? `event-${event.severity}` : ''}>
            <div className="event-time"><strong>{event.time}</strong><small>{event.date}</small></div>
            <div className="timeline-rail"><i />{index < events.length - 1 && <span />}</div>
            <div className="event-copy"><h3>{event.title}</h3><p>{event.description}</p><small><Clock3 size={11} /> {event.entities.length} linked entities</small></div>
          </article>
        ))}
      </div>
    </section>
  )
}
