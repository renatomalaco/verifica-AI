export type ThreatLevel = 'SEGURO' | 'CUIDADO' | 'GOLPE' | 'INCONCLUSIVO'

export type Channel = 'texto' | 'url' | 'imagem'

export type Persuasion = 'urgencia' | 'ameaca_financeira' | 'coercao_afetiva' | 'nenhuma'

export interface ScanRequest {
  content: string
  image_b64?: string | null
}

export interface ScanDetails {
  channel: Channel
  deciding_stage: string
  category?: string | null
  scores: Record<string, number>
  domain_signals?: Record<string, string> | null
  links_not_inspected?: boolean
  latency_breakdown?: Record<string, number>
}

export interface ScanResponse {
  id: string
  threat_level: ThreatLevel
  verdict_plain: string
  action_advice: string
  details: ScanDetails
}

export type StageName =
  | 'triage'
  | 'stage_0_cache'
  | 'stage_1_signals'
  | 'stage_2_inspection'
  | 'image_extraction'
  | 'visual_rag'
  | string

export type StageStatus = 'pending' | 'started' | 'done' | 'skipped'

export interface StageEvent {
  stage: StageName
  status: 'started' | 'done' | 'skipped'
}

export type ScannerStatus = 'IDLE' | 'SCANNING' | 'RESULT' | 'ERROR'

export type InputTab = 'text' | 'url' | 'image'

// "Me explica" response (plan item R5b: POST /api/v1/scans/{id}/explain).
export interface ExplainResponse {
  lines: string[]
  remaining_today?: number
}
