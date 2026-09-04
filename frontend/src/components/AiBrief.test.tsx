import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import type { InvestigationBriefing } from '../types'
import { AiBrief } from './AiBrief'

const briefing = {
  findings: [{
    id: 'repeat-subject-network',
    severity: 'high',
    title: '61 repeat-subject patterns require review',
    summary: 'Named subjects occur in two or more independently recorded cases.',
    confidence: 100,
    basis: 'direct graph count',
    evidence: [{ entity: 'Dante Thomas', case_count: 3, case_ids: ['JC1', 'JC2', 'JC3'] }],
    alternatives: ['Names may refer to different people'],
    next_action: 'Verify identity attributes in the original FIRs.',
  }],
  guardrails: ['Human review required.', 'Risk scores do not establish guilt.'],
} as unknown as InvestigationBriefing

function Harness() {
  const [expanded, setExpanded] = useState(false)
  return <AiBrief briefing={briefing} expanded={expanded} onToggle={() => setExpanded(!expanded)}/>
}

describe('AiBrief', () => {
  it('reveals evidence, alternatives, and the human review action', () => {
    render(<Harness/>)
    fireEvent.click(screen.getByRole('button', { name: /explain finding/i }))
    expect(screen.getByText('Source-linked evidence')).toBeInTheDocument()
    expect(screen.getByText('Alternative explanations')).toBeInTheDocument()
    expect(screen.getByText('Verify identity attributes in the original FIRs.')).toBeInTheDocument()
    expect(screen.getByText('Risk scores do not establish guilt.')).toBeInTheDocument()
  })
})
