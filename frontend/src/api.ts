import { graphData } from './data/mockData'
import type { AlertItem, AnalyticsDistribution, AuditAnchors, AuditAnchorRecord, AuditVerification, AuthUser, CentralityResult, ConnectionPath, CounterfactualResult, FusionAssurance, GraphData, GraphSageAnalysis, IdentityCandidate, InvestigationBriefing, InvestigationWorkspace, LocationSignal, ModelEvaluation, MotifResponse, PipelineRun, ProtectedProfile, RiskTrendPoint, ScaleBenchmark, SurakshaEvaluation, SurakshaReplay, SystemReadiness, TemporalEmergence, TimelineEvent, UploadRecord } from './types'

const TOKEN_KEY = 'sentinel-access-token'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

const requestOptions = (options: RequestInit = {}): RequestInit => {
  const headers = new Headers(options.headers)
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  return { ...options, headers }
}

const json = async <T>(path: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(path, requestOptions(options))
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null
    throw new ApiError(response.status, payload?.detail || `Request failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  async getCurrentUser(): Promise<AuthUser> {
    return json<AuthUser>('/api/auth/me')
  },

  async login(email: string, password: string): Promise<AuthUser> {
    const result = await json<{ access_token: string; user: Omit<AuthUser, 'mode'> }>('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    localStorage.setItem(TOKEN_KEY, result.access_token)
    return { ...result.user, mode: 'authenticated' }
  },

  logout() {
    localStorage.removeItem(TOKEN_KEY)
  },

  async download(path: string, filename: string): Promise<void> {
    const response = await fetch(path, requestOptions())
    if (!response.ok) throw new ApiError(response.status, `Export failed: ${response.status}`)
    const url = URL.createObjectURL(await response.blob())
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  },

  async getGraph(): Promise<GraphData> {
    try {
      return await json<GraphData>('/api/visualization/graph')
    } catch {
      return graphData
    }
  },

  async getAlerts(): Promise<AlertItem[]> {
    return json<AlertItem[]>('/api/alerts')
  },

  async getGraphSageAnalysis(limit = 8): Promise<GraphSageAnalysis> {
    return json<GraphSageAnalysis>(`/api/analytics/graphsage?limit=${limit}`)
  },

  async upload(file: File): Promise<UploadRecord> {
    const form = new FormData()
    form.append('file', file)
    return json<UploadRecord>('/api/upload', { method: 'POST', body: form })
  },

  async getUploads(): Promise<UploadRecord[]> {
    return json<UploadRecord[]>('/api/uploads')
  },

  async startPipeline(uploadId: string, activate = true): Promise<{ pipeline_id: string }> {
    return json<{ pipeline_id: string }>('/api/pipeline/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ upload_id: uploadId, activate }),
    })
  },

  async getPipelineStatus(pipelineId: string): Promise<PipelineRun> {
    return json<PipelineRun>(`/api/pipeline/status/${pipelineId}`)
  },

  async getBriefing(): Promise<InvestigationBriefing> {
    return json<InvestigationBriefing>('/api/analysis/briefing')
  },

  async getTimeline(): Promise<TimelineEvent[]> {
    return json<TimelineEvent[]>('/api/visualization/timeline')
  },

  async getLocations(): Promise<LocationSignal[]> {
    return json<LocationSignal[]>('/api/visualization/locations')
  },

  async getAnalyticsDistribution(): Promise<AnalyticsDistribution> {
    return json<AnalyticsDistribution>('/api/analytics/distribution')
  },

  async getRiskTrends(): Promise<RiskTrendPoint[]> {
    const result = await json<{ items: RiskTrendPoint[] }>('/api/analytics/trends')
    return result.items
  },

  async getCentrality(metric: CentralityResult['metric'] = 'influence', limit = 8, entityType?: string): Promise<CentralityResult[]> {
    return json<CentralityResult[]>(`/api/analytics/centrality?metric=${metric}&limit=${limit}${entityType ? `&entity_type=${encodeURIComponent(entityType)}` : ''}`)
  },

  async getConnectionPath(sourceId: string, targetId: string, maxHops = 8): Promise<ConnectionPath> {
    return json<ConnectionPath>(`/api/analysis/connection-path?source_id=${encodeURIComponent(sourceId)}&target_id=${encodeURIComponent(targetId)}&max_hops=${maxHops}`)
  },

  async getCounterfactual(nodeId: string): Promise<CounterfactualResult> {
    return json<CounterfactualResult>(`/api/analysis/counterfactual/${encodeURIComponent(nodeId)}`)
  },

  async getMotifs(limit = 25): Promise<MotifResponse> {
    return json<MotifResponse>(`/api/analysis/motifs?limit=${limit}`)
  },

  async getSurakshaReplay(): Promise<SurakshaReplay> {
    return json<SurakshaReplay>('/api/demo/suraksha/replay')
  },

  async getSurakshaEvaluation(): Promise<SurakshaEvaluation> {
    return json<SurakshaEvaluation>('/api/demo/suraksha/evaluation')
  },

  async getSurakshaFusionAssurance(): Promise<FusionAssurance> {
    return json<FusionAssurance>('/api/demo/suraksha/fusion-assurance')
  },

  async getSurakshaEmergence(): Promise<TemporalEmergence> {
    return json<TemporalEmergence>('/api/demo/suraksha/emergence')
  },

  async getIdentityCandidates(): Promise<IdentityCandidate[]> {
    const result = await json<{ items: IdentityCandidate[] }>('/api/entity-resolution/candidates')
    return result.items
  },

  async decideIdentityCandidate(id: string, decision: 'keep-separate' | 'escalate', rationale: string): Promise<void> {
    await json(`/api/entity-resolution/${encodeURIComponent(id)}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, rationale }),
    })
  },

  async resetSuraksha(): Promise<void> {
    await json('/api/demo/suraksha/reset', { method: 'POST' })
  },

  async getProtectedPeople(): Promise<ProtectedProfile[]> {
    const result = await json<{ items: ProtectedProfile[] }>('/api/protected-persons')
    return result.items
  },

  async revealProtectedPerson(id: string, reason: string, authorizationReference: string): Promise<ProtectedProfile> {
    return json<ProtectedProfile>(`/api/protected-persons/${encodeURIComponent(id)}/reveal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason, authorization_reference: authorizationReference }),
    })
  },

  async getAuditVerification(): Promise<AuditVerification> {
    return json<AuditVerification>('/api/audit/verify')
  },

  async getAuditAnchors(): Promise<AuditAnchors> {
    return json<AuditAnchors>('/api/audit/anchors')
  },

  async createAuditAnchor(submit: boolean): Promise<AuditAnchorRecord> {
    return json<AuditAnchorRecord>('/api/audit/anchors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ submit }),
    })
  },

  async refreshAuditAnchor(id: string): Promise<AuditAnchorRecord> {
    return json<AuditAnchorRecord>(`/api/audit/anchors/${encodeURIComponent(id)}/refresh`, { method: 'POST' })
  },

  async downloadAuditAnchor(id: string, proof = true): Promise<void> {
    const suffix = proof ? 'proof' : 'checkpoint'
    const extension = proof ? 'checkpoint.json.ots' : 'checkpoint.json'
    return this.download(`/api/audit/anchors/${encodeURIComponent(id)}/${suffix}`, `${id}.${extension}`)
  },

  async downloadAuditAnchorBundle(id: string): Promise<void> {
    return this.download(`/api/audit/anchors/${encodeURIComponent(id)}/bundle`, `${id}.proof-bundle.zip`)
  },

  async getReadiness(): Promise<SystemReadiness> {
    return json<SystemReadiness>('/api/system/readiness')
  },

  async getScaleBenchmark(): Promise<ScaleBenchmark> {
    return json<ScaleBenchmark>('/api/benchmarks/scale')
  },

  async getModelEvaluation(): Promise<ModelEvaluation> {
    return json<ModelEvaluation>('/api/benchmarks/model')
  },

  async getInvestigations(): Promise<InvestigationWorkspace> {
    return json<InvestigationWorkspace>('/api/investigations')
  },

  async activateInvestigation(id: string): Promise<void> {
    await json(`/api/investigations/${encodeURIComponent(id)}/activate`, { method: 'POST' })
  },

  async acknowledgeAlert(alertId: string): Promise<void> {
    await json(`/api/alerts/${alertId}/acknowledge`, { method: 'POST' })
  },

  exportUrl(format: string) {
    return `/api/export/graph/${format}`
  },
}
