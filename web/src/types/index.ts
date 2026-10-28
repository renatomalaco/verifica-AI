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

// Message codes from packages/contracts (VerdictMessage). The backend decides,
// the front end words them through the message dictionary.
export const VERDICT_MESSAGES = [
  'scam_affective_coercion',
  'scam_financial_threat',
  'scam_urgency',
  'scam_brand_spoofing',
  'scam_generic',
  'caution',
  'safe',
  'inconclusive',
] as const

export type VerdictMessage = (typeof VERDICT_MESSAGES)[number]

export interface ScanResponse {
  id: string
  threat_level: ThreatLevel
  verdict_message: VerdictMessage
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

// Ablation study report served by the research-runner (GET /pesquisa/report).
export type ResearchModeName = 'heuristic' | 'classical_nlp' | 'pure_vlm' | 'cascade'

export interface ResearchMetrics {
  accuracy: number
  precision: number
  recall: number
  f1_score: number
  f2_score: number
  ece: number
  p95_latency_ms: number
  cost_per_1k_usd: number
  total_samples: number
}

export interface ResearchMode {
  mode: ResearchModeName
  status: 'executed' | 'not_executed'
  note?: string | null
  metrics?: ResearchMetrics
}

export interface ResearchReport {
  meta: {
    generated_at: string
    seed: number
    split: { train: number; test: number }
    triage: string
    disabled_stages: string[]
    warnings: string[]
  }
  modes: ResearchMode[]
  adversarial: { total: number; detected_without_sanitization: number; detected_with_sanitization: number }
  latex_table: string
}
