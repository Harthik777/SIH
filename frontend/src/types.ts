export type EntityType = 'person' | 'protected_person' | 'organization' | 'location' | 'account' | 'phone' | 'event' | 'vehicle' | 'crime'
export type Severity = 'critical' | 'high' | 'medium' | 'low'

export interface AuthUser {
  email: string
  role: 'viewer' | 'analyst' | 'supervisor' | 'demo'
  mode: string
}

export interface GraphNode {
  id: string
  name: string
  type: EntityType
  risk: number
  confidence: number
  community: number
  aliases?: string[]
  description?: string
  location?: string
  lastSeen?: string
  tags?: string[]
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  label: string
  confidence: number
  anomalous?: boolean
  evidence_record_ids?: string[]
  evidence_hashes?: string[]
  source_types?: string[]
  observed_at?: string
  epistemic_status?: 'observed' | 'derived'
}

export interface AlertItem {
  id: string
  title: string
  detail: string
  severity: Severity
  time: string
  entityId: string
  acknowledged: boolean
  confidence: number
}

export interface TimelineEvent {
  id: string
  date: string
  time: string
  title: string
  description: string
  type: EntityType | 'transaction'
  severity?: Severity
  entities: string[]
  occurred_at?: string
  risk?: number
  case_id?: string
}

export interface PipelineStage {
  id: string
  name: string
  detail: string
  progress: number
  status: 'queued' | 'running' | 'complete' | 'failed'
}

export interface PipelineRun {
  id: string
  upload_id: string
  status: 'queued' | 'running' | 'complete' | 'failed'
  progress: number
  stages: Array<Omit<PipelineStage, 'detail'>>
  logs: string[]
  result: {
    source?: { records: number; sha256: string; format: string }
    graph?: { nodes: number; edges: number }
    risk_signals?: number
    investigation?: Investigation & { active: boolean }
  }
  error?: string
}

export interface Investigation {
  id: string
  name: string
  source: string
  source_type: string
  records: number
  nodes?: number
  edges?: number
  created_at: string
  status: string
  built_in: boolean
  active?: boolean
}

export interface InvestigationWorkspace {
  active_id: string
  items: Investigation[]
  persistence: string
}

export interface LocationSignal {
  id: string
  name: string
  x: number
  y: number
  lat: number
  lng: number
  count: number
  risk: number
  entity_id: string
  coordinate_basis: string
}

export interface CentralityResult {
  node: GraphNode
  rank: number
  score: number
  metric: 'influence' | 'degree' | 'betweenness' | 'reach'
  degree: number
  degree_centrality: number
  betweenness_approx: number
  neighborhood_reach: number
  method: string
}

export interface AnalyticsDistribution {
  entity_types: Record<string, number>
  relationship_types: Record<string, number>
  risk_bands: Record<string, number>
  degree_distribution: Array<{ degree: number; nodes: number }>
  structure: {
    nodes: number
    edges: number
    components: number
    average_degree: number
    density: number
    modularity: number
    max_degree: number
    average_risk: number
  }
}

export interface RiskTrendPoint {
  period: string
  average_risk: number
  review_signals: number
  incidents: number
}

export interface InvestigationFinding {
  id: string
  severity: Severity
  title: string
  summary: string
  confidence: number
  basis: string
  evidence: Array<Record<string, unknown>>
  alternatives: string[]
  next_action: string
}

export interface InvestigationBriefing {
  investigation: string
  generated_at: string
  operating_mode: string
  risk_posture: string
  graph: { nodes: number; edges: number; repeat_suspects: number }
  quality: {
    records: number
    required_field_completeness: number
    unique_case_numbers: number
    duplicate_case_numbers: number
    suspect_coverage: number
    vehicle_plate_coverage: number
    ontology_mapping_coverage: number
    quality_gate: string
  }
  model: GraphSageAnalysis['model']
  provenance: { verified: number; total: number }
  findings: InvestigationFinding[]
  guardrails: string[]
}

export interface UploadRecord {
  id: string
  filename: string
  size: number
  created_at: string
  status: string
  records: number
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface TracePathStep {
  from: GraphNode
  relationship: string
  to: GraphNode
  edge_id: string
  confidence: number
  anomalous: boolean
  direction: 'forward' | 'reverse traversal'
  evidence_status: 'stored-observation'
  evidence_record_ids: string[]
  evidence_hashes: string[]
  source_types: string[]
  observed_at: string | null
}

export interface ConnectionPath {
  found: boolean
  source: GraphNode
  target: GraphNode
  hops: number | null
  path_confidence: number | null
  steps: TracePathStep[]
  method: string
  epistemic_status: 'observed-path' | 'no-observed-path'
  guardrail?: string
  receipt: string
}

export interface CounterfactualResult {
  entity: GraphNode
  factors: Array<{ factor: string; value: number; basis: string | string[]; kind: 'observed' | 'derived' }>
  scenarios: Array<{ change: string; risk_after: number; delta: number; required_verification: string }>
  method: string
  epistemic_status: 'counterfactual-decision-support'
  guardrail: string
  receipt: string
}

export interface TemporalMotif {
  id: string
  type: 'rapid-repeat' | 'repeat-subject' | 'area-concentration'
  severity: Severity
  title: string
  summary: string
  subject: GraphNode
  case_ids: string[]
  case_names: string[]
  location_ids: string[]
  minimum_gap_days: number | null
  time_start: string | null
  time_end: string | null
  confidence: number
  evidence_status: 'derived-from-observed-paths'
  alternative: string
  receipt: string
}

export interface MotifResponse {
  method: string
  epistemic_status: 'derived-investigative-leads'
  guardrail: string
  items: TemporalMotif[]
  total: number
  receipt: string
}

export interface ReplayStep {
  order: number
  time: string
  source: string
  title: string
  finding: string
  evidence_ids: string[]
  status: 'observation' | 'derived-lead' | 'human-review'
  receipt: string
}

export interface SurakshaReplay {
  investigation_id: string
  title: string
  subtitle: string
  classification: string
  source_counts: Record<string, number>
  records: number
  nodes: number
  edges: number
  steps: ReplayStep[]
  guardrail: string
  receipt: string
}

export interface SurakshaEvaluation {
  investigation_id: string
  classification: string
  summary: {
    entities_recovered: number
    entities_expected: number
    relationships_recovered: number
    relationships_expected: number
    hidden_path_recovered: boolean
    false_merges: number
    processing_mode: string
  }
  expected_path: { source: string; target: string; found: boolean; hops: number | null; trace_receipt: string | null }
  negative_identity_control: { left: string; right: string; expected_decision: string; reason: string; distinct_nodes_preserved: boolean }
  scope_note: string
  receipt: string
}

export interface FusionPattern {
  id: string
  type: string
  title: string
  severity: Severity
  confidence: number
  evidence_status: 'derived-lead-from-recorded-observations'
  source_types: string[]
  evidence_record_ids: string[]
  evidence_records: Array<{ id: string; source_type: string; sha256: string }>
  time_start: string | null
  time_end: string | null
  explanation: string
  alternative: string
  analyst_action: string
  method: string
  receipt: string
}

export interface FusionAssurance {
  classification: 'synthetic-acceptance-evaluation'
  method: string
  summary: {
    checks_passed: number
    checks_total: number
    patterns_recovered: number
    patterns_expected: number
    edge_provenance_coverage: number
    source_channels: number
  }
  checks: Array<{ id: string; label: string; passed: boolean; detail: string }>
  patterns: FusionPattern[]
  scope_note: string
  receipt: string
}

export interface TemporalEmergence {
  method: string
  snapshots: Array<{
    date: string
    new_records: number
    cumulative_records: number
    cumulative_nodes: number
    cumulative_edges: number
    source_types_seen: string[]
    patterns_detected: number
    new_patterns: string[]
  }>
  guardrail: string
  receipt: string
}

export interface IdentityCandidate {
  id: string
  left: GraphNode
  right: GraphNode
  similarity: number
  supporting_signals: string[]
  conflicting_signals: string[]
  recommendation: 'keep-separate' | 'escalate'
  status: string
  decision?: { decision: string; rationale: string; effect: string } | null
  guardrail: string
  receipt: string
}

export interface ProtectedProfile {
  id: string
  graph_name: string
  name: string
  phone: string
  address: string
  status: 'masked' | 'revealed-for-current-response'
  risk_scoring?: 'prohibited'
  synthetic?: boolean
  audit_hash?: string
  guardrail: string
}

export interface AuditVerification {
  valid: boolean
  entries: number
  head: string
  errors: Array<{ sequence: number | null; reason: string }>
  method: string
  scope_note: string
}

export interface ReadinessCheck {
  id: string
  label: string
  passed: boolean
  detail: string
  required: boolean
}

export interface SystemReadiness {
  ready: boolean
  offline_capable: boolean
  external_services_required: boolean
  public_demo: boolean
  active_investigation: { id: string; name: string }
  checks: ReadinessCheck[]
  audit: AuditVerification
  scope_note: string
}

export interface ScaleBenchmark {
  generated_at: string
  classification: string
  runs: Array<{
    records: number
    graph_build_seconds: number
    throughput_records_per_second: number
    nodes: number
    edges: number
    peak_python_memory_mib: number
    linear_search: { median_ms: number; p95_ms: number }
    connection_path: { median_ms: number; p95_ms: number; hops: number | null }
  }>
  entity_resolution_safety: { false_merge_rate: number; automatic_merge_precision: number | null; precision_note: string }
}

export interface ModelEvaluation {
  schema_version: number
  classification: string
  dataset: { suspects: number; positive_suspects: number; label_definition: string }
  graphsage: {
    runtime_mode: string
    threshold: number
    reproduction_diagnostic: {
      role: string
      reported_reproduced_f1: number
      full_supplied_graph: {
        metrics: { precision: number; recall: number; f1: number; accuracy: number; false_positive: number; false_negative: number }
        brier_score: number | null
      }
      checkpoint_selection_partition: {
        samples: number
        positive_samples: number
        split_seed: number
        split_type: string
        metrics: { precision: number; recall: number; f1: number; accuracy: number; false_positive: number; false_negative: number }
        brier_score: number | null
        independent_outcome_labels: boolean
        used_for_checkpoint_selection: boolean
      }
    }
    evidence_masking_stress_test: {
      purpose: string
      mask_rate: number
      trials: number
      masked_case_edges_per_trial: number
      summary: Record<'precision' | 'recall' | 'f1' | 'accuracy', { mean: number; min: number; max: number }>
      brier_score: { mean: number; min: number; max: number } | null
      independent_outcome_labels: boolean
      generalization_claim_allowed: boolean
    }
  }
  fixed_baselines: Record<string, { precision: number; recall: number; f1: number; accuracy: number }>
  leakage_audit: {
    status: string
    target_derived_from_input_graph: boolean
    checkpoint_selected_on_reported_partition: boolean
    independent_labels: boolean
    identity_disjoint_test: boolean
    temporal_holdout: boolean
    conclusion: string
  }
  claim_assurance: {
    field_accuracy: string
    operational_use: string
    feature_target_dependency: string
    dependency_explanation: string
    permitted_claim: string
    prohibited_claims: string[]
    release_gate: string
  }
  limitations: string[]
}

export interface GraphSageResult {
  node_id: string
  name: string
  case_neighbors: number
  graph_degree: number
  feature_vector: number[]
  derived_label: 'normal' | 'suspicious'
  probability: number | null
  risk: number
}

export interface GraphSageAnalysis {
  model: {
    id: string
    name: string
    status: 'ready' | 'checkpoint-required' | 'runtime-required' | 'schema-review'
    mode: string
    message: string
    architecture: {
      input_features: number
      hidden_channels: number[]
      output_classes: string[]
    }
    training_summary: {
      nodes: number
      edges: number
      suspects: number
      positive_suspects: number
      reported_reproduction_f1: number
      metric_role: string
      reproduced_checkpoint?: {
        reproduction_f1: number
        metric_role: string
        best_epoch: number
        model_seed: number
      }
    }
    artifacts: {
      checkpoint_available: boolean
      runtime_available: boolean
    }
  }
  mode: string
  message: string
  items: GraphSageResult[]
  count: number
  privacy_exclusions?: number
}
