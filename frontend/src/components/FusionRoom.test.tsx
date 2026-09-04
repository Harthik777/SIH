import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { api } from '../api'
import type { IdentityCandidate, SurakshaEvaluation, SurakshaReplay } from '../types'
import { FusionRoom } from './FusionRoom'

vi.mock('../api', () => ({
  api: {
    getSurakshaReplay: vi.fn(),
    getSurakshaEvaluation: vi.fn(),
    getIdentityCandidates: vi.fn(),
    decideIdentityCandidate: vi.fn(),
    getProtectedPeople: vi.fn(),
    revealProtectedPerson: vi.fn(),
    getAuditVerification: vi.fn(),
    getReadiness: vi.fn(),
    getScaleBenchmark: vi.fn(),
    resetSuraksha: vi.fn(),
  },
}))

const replay: SurakshaReplay = {
  investigation_id: 'operation-suraksha',
  title: 'Operation Suraksha',
  subtitle: 'Synthetic multi-source evidence-fusion exercise',
  classification: 'SYNTHETIC · NO REAL PERSON OR CASE DATA',
  source_counts: { FIR: 6, CDR: 10, BANK: 7, ANPR: 4, SURVEILLANCE: 3, OSINT: 2 },
  records: 32,
  nodes: 64,
  edges: 148,
  steps: [
    { order: 1, time: '18 Aug · 19:10', source: 'FIR', title: 'First complaint establishes identifiers', finding: 'Observation.', evidence_ids: ['event:1'], status: 'observation', receipt: 'a'.repeat(64) },
    { order: 2, time: '24 Aug · 10:02', source: 'IDENTITY CONTROL', title: 'False merge is deliberately prevented', finding: 'Contradictory identifiers keep both people separate.', evidence_ids: ['event:2'], status: 'human-review', receipt: 'b'.repeat(64) },
  ],
  guardrail: 'This replay does not determine identity, intent, culpability, or enforcement action.',
  receipt: 'c'.repeat(64),
}

const evaluation: SurakshaEvaluation = {
  investigation_id: 'operation-suraksha',
  classification: 'synthetic-evaluation-only',
  summary: { entities_recovered: 14, entities_expected: 14, relationships_recovered: 6, relationships_expected: 6, hidden_path_recovered: true, false_merges: 0, processing_mode: 'deterministic-local' },
  expected_path: { source: 'Subject A-17', target: 'Coordinator C-04', found: true, hops: 6, trace_receipt: 'd'.repeat(64) },
  negative_identity_control: { left: 'Kavya Rao', right: 'K. Rao', expected_decision: 'keep-separate', reason: 'Conflicting identifiers', distinct_nodes_preserved: true },
  scope_note: 'Synthetic scenario acceptance checks, not a real-world accuracy claim.',
  receipt: 'e'.repeat(64),
}

const candidate: IdentityCandidate = {
  id: 'suraksha-identity-kr',
  left: { id: 'person:kavya', name: 'Kavya Rao', type: 'person', risk: 10, confidence: 100, community: 1 },
  right: { id: 'person:k-rao', name: 'K. Rao', type: 'person', risk: 10, confidence: 100, community: 2 },
  similarity: 0.38,
  supporting_signals: ['Similar abbreviated name'],
  conflicting_signals: ['Distinct phone identifiers', 'Incompatible locations'],
  recommendation: 'keep-separate',
  status: 'pending-review',
  decision: null,
  guardrail: 'Name similarity alone is insufficient to merge identities.',
  receipt: 'f'.repeat(64),
}

describe('FusionRoom', () => {
  it('replays cross-source evidence and exposes the safe identity control', async () => {
    vi.mocked(api.getSurakshaReplay).mockResolvedValue(replay)
    vi.mocked(api.getSurakshaEvaluation).mockResolvedValue(evaluation)
    vi.mocked(api.getIdentityCandidates).mockResolvedValue([candidate])
    vi.mocked(api.decideIdentityCandidate).mockResolvedValue()
    vi.mocked(api.getProtectedPeople).mockResolvedValue([{ id: 'PP-S-001', graph_name: 'Protected Person S-01', name: 'N•••••• R••', phone: '+91-•••••••001', address: 'WITHHELD — Karnataka', status: 'masked', risk_scoring: 'prohibited', guardrail: 'Protected' }])
    vi.mocked(api.getAuditVerification).mockResolvedValue({ valid: true, entries: 2, head: 'a'.repeat(64), errors: [], method: 'sha256-chain-v1', scope_note: 'Local' })
    vi.mocked(api.getReadiness).mockResolvedValue({ ready: true, offline_capable: true, external_services_required: false, public_demo: false, active_investigation: { id: 'operation-suraksha', name: 'Operation Suraksha' }, checks: [], audit: { valid: true, entries: 2, head: 'a'.repeat(64), errors: [], method: 'sha256-chain-v1', scope_note: 'Local' }, scope_note: 'Ready' })
    vi.mocked(api.getScaleBenchmark).mockResolvedValue({ generated_at: '2026-09-04', classification: 'synthetic-performance-evaluation', runs: [], entity_resolution_safety: { false_merge_rate: 0, automatic_merge_precision: null, precision_note: 'Not applicable' } })
    vi.mocked(api.resetSuraksha).mockResolvedValue()

    render(<FusionRoom activeId="operation-suraksha" onActivate={vi.fn()} onOpenTrace={vi.fn()}/>)

    expect(await screen.findByText('14')).toBeInTheDocument()
    expect(screen.getByText('Masked by default. Never scored.')).toBeInTheDocument()
    expect(screen.getByText('VALID')).toBeInTheDocument()
    expect(screen.getByText('Prevent the dangerous merge')).toBeInTheDocument()
    expect(screen.getByText('Kavya Rao')).toBeInTheDocument()
    expect(screen.getByText('K. Rao')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /false merge is deliberately prevented/i }))
    expect(screen.getByText('Contradictory identifiers keep both people separate.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /keep separate/i }))
    await waitFor(() => expect(api.decideIdentityCandidate).toHaveBeenCalledWith(
      'suraksha-identity-kr',
      'keep-separate',
      expect.stringContaining('Distinct phones'),
    ))
  })
})
