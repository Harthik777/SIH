import { graphData } from './data/mockData'
import type { AlertItem, AnalyticsDistribution, AuditVerification, CentralityResult, ConnectionPath, CounterfactualResult, GraphData, GraphSageAnalysis, IdentityCandidate, InvestigationBriefing, InvestigationWorkspace, LocationSignal, MotifResponse, PipelineRun, ProtectedProfile, RiskTrendPoint, ScaleBenchmark, SurakshaEvaluation, SurakshaReplay, SystemReadiness, TimelineEvent, UploadRecord } from './types'

const json = async <T>(path: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(path, options)
  if (!response.ok) throw new Error(`Request failed: ${response.status}`)
  return response.json() as Promise<T>
}

export const api = {
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

  async getReadiness(): Promise<SystemReadiness> {
    return json<SystemReadiness>('/api/system/readiness')
  },

  async getScaleBenchmark(): Promise<ScaleBenchmark> {
    return json<ScaleBenchmark>('/api/benchmarks/scale')
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
