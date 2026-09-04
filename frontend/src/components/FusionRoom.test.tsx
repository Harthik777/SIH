import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { api } from '../api'
import type { FusionAssurance, IdentityCandidate, SurakshaEvaluation, SurakshaReplay, TemporalEmergence } from '../types'
import { FusionRoom } from './FusionRoom'

vi.mock('../api', () => ({
  api: {
    getSurakshaReplay: vi.fn(),
    getSurakshaEvaluation: vi.fn(),
    getSurakshaFusionAssurance: vi.fn(),
    getSurakshaEmergence: vi.fn(),
    getIdentityCandidates: vi.fn(),
    decideIdentityCandidate: vi.fn(),
    getProtectedPeople: vi.fn(),
    revealProtectedPerson: vi.fn(),
    getAuditVerification: vi.fn(),
    getAuditAnchors: vi.fn(),
    createAuditAnchor: vi.fn(),
    refreshAuditAnchor: vi.fn(),
    downloadAuditAnchor: vi.fn(),
    downloadAuditAnchorBundle: vi.fn(),
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

const fusionAssurance: FusionAssurance = {
  classification: 'synthetic-acceptance-evaluation', method: 'suraksha-fusion-rules-v1',
  summary: { checks_passed: 5, checks_total: 5, patterns_recovered: 5, patterns_expected: 5, edge_provenance_coverage: 100, source_channels: 6 },
  checks: [{ id: 'edge-provenance', label: 'Every graph relationship carries provenance', passed: true, detail: '148 of 148' }],
  patterns: [{ id: 'circular-fund-flow', type: 'directed-account-cycle', title: 'Circular fund movement', severity: 'critical', confidence: 94, evidence_status: 'derived-lead-from-recorded-observations', source_types: ['BANK'], evidence_record_ids: ['TX-S-001', 'TX-S-003', 'TX-S-004'], evidence_records: [{ id: 'TX-S-001', source_type: 'BANK', sha256: 'z'.repeat(64) }], time_start: '2026-08-18T19:22:00', time_end: '2026-08-19T08:05:00', explanation: 'Recorded transfers form a three-account cycle.', alternative: 'Related-party settlements can create cycles.', analyst_action: 'Confirm beneficial ownership.', method: 'suraksha-fusion-rules-v1', receipt: 'g'.repeat(64) }],
  scope_note: 'Synthetic acceptance only.', receipt: 'h'.repeat(64),
}

const emergence: TemporalEmergence = {
  method: 'suraksha-fusion-rules-v1',
  snapshots: [{ date: '2026-08-18', new_records: 9, cumulative_records: 11, cumulative_nodes: 27, cumulative_edges: 54, source_types_seen: ['FIR', 'CDR'], patterns_detected: 2, new_patterns: ['communication-burst'] }],
  guardrail: 'Timestamp reconstruction, not a forecast.', receipt: 'i'.repeat(64),
}

describe('FusionRoom', () => {
  it('replays cross-source evidence and exposes the safe identity control', async () => {
    vi.mocked(api.getSurakshaReplay).mockResolvedValue(replay)
    vi.mocked(api.getSurakshaEvaluation).mockResolvedValue(evaluation)
    vi.mocked(api.getSurakshaFusionAssurance).mockResolvedValue(fusionAssurance)
    vi.mocked(api.getSurakshaEmergence).mockResolvedValue(emergence)
    vi.mocked(api.getIdentityCandidates).mockResolvedValue([candidate])
    vi.mocked(api.decideIdentityCandidate).mockResolvedValue()
    vi.mocked(api.getProtectedPeople).mockResolvedValue([{ id: 'PP-S-001', graph_name: 'Protected Person S-01', name: 'N•••••• R••', phone: '+91-•••••••001', address: 'WITHHELD — Karnataka', status: 'masked', risk_scoring: 'prohibited', guardrail: 'Protected' }])
    vi.mocked(api.getAuditVerification).mockResolvedValue({ valid: true, entries: 2, head: 'a'.repeat(64), errors: [], method: 'sha256-chain-v1', scope_note: 'Local' })
    const anchorService = { connectivity_mode: 'hybrid' as const, online_capable: true, provider: 'OpenTimestamps / Bitcoin', submission_enabled: true, submitted_checkpoints: 0, submission_attempts: 0, public_submission_limit: 3, latest: null, privacy_boundary: 'Only a blinded commitment leaves Sentinel.', confirmation_boundary: 'Calendar acceptance is pending until Bitcoin confirmation.' }
    vi.mocked(api.getAuditAnchors).mockResolvedValue({ items: [], service: anchorService })
    vi.mocked(api.createAuditAnchor).mockResolvedValue({ id: 'ots-checkpoint', created_at: '2026-09-05T00:00:00Z', created_by: 'supervisor', status: 'calendar-pending', provider: 'OpenTimestamps / Bitcoin', audit_head: 'a'.repeat(64), audit_entries: 2, checkpoint_sha256: 'b'.repeat(64), calendar_commitment: 'c'.repeat(64), calendars_accepted: ['https://a.pool.opentimestamps.org'], proof_available: true, bitcoin: null, last_error: null, scope_note: 'Pending' })
    vi.mocked(api.getReadiness).mockResolvedValue({ ready: true, offline_capable: true, online_capable: true, connectivity_mode: 'hybrid', external_services_required: false, public_demo: false, active_investigation: { id: 'operation-suraksha', name: 'Operation Suraksha' }, checks: [], audit: { valid: true, entries: 2, head: 'a'.repeat(64), errors: [], method: 'sha256-chain-v1', scope_note: 'Local' }, anchoring: anchorService, scope_note: 'Ready' })
    vi.mocked(api.getScaleBenchmark).mockResolvedValue({ generated_at: '2026-09-04', classification: 'synthetic-performance-evaluation', runs: [], entity_resolution_safety: { false_merge_rate: 0, automatic_merge_precision: null, precision_note: 'Not applicable' } })
    vi.mocked(api.resetSuraksha).mockResolvedValue()

    render(<FusionRoom activeId="operation-suraksha" onActivate={vi.fn()} onOpenTrace={vi.fn()}/>)

    expect(await screen.findByText('14')).toBeInTheDocument()
    expect(screen.getByText('Masked by default. Never scored.')).toBeInTheDocument()
    expect(screen.getByText('VALID')).toBeInTheDocument()
    expect(screen.getByText('HYBRID')).toBeInTheDocument()
    expect(screen.getByText('Bitcoin timestamp via OpenTimestamps')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /anchor current head/i }))
    await waitFor(() => expect(api.createAuditAnchor).toHaveBeenCalledWith(true))
    expect(screen.getByText('Prevent the dangerous merge')).toBeInTheDocument()
    expect(screen.getByText('Circular fund movement')).toBeInTheDocument()
    expect(screen.getByText('100%')).toBeInTheDocument()
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
