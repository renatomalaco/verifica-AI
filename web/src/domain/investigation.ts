// Investigation rules: what is sent, how stages progress and what to say when something fails.
import { m } from '../paraglide/messages.js'
import type { InputTab, ScanRequest, StageEvent, StageStatus } from '../types'

export interface EvidenceData {
  tab: InputTab
  content: string
  imageB64: string | null
}

export interface StageEntry {
  stage: string
  status: StageStatus
}

export function buildEvidence(tab: InputTab, content: string, imageB64: string | null): EvidenceData | null {
  if (tab === 'image') return imageB64 ? { tab, content: '', imageB64 } : null
  const text = content.trim()
  return text ? { tab, content: text, imageB64: null } : null
}

export function toScanRequest(evidence: EvidenceData): ScanRequest {
  return {
    content: evidence.content,
    image_b64: evidence.imageB64 ? evidence.imageB64.replace(/^data:image\/[a-zA-Z+]+;base64,/, '') : null,
  }
}

export function upsertStage(stages: StageEntry[], event: StageEvent): StageEntry[] {
  const entry = { stage: event.stage, status: event.status }
  const exists = stages.some((s) => s.stage === event.stage)
  return exists ? stages.map((s) => (s.stage === event.stage ? entry : s)) : [...stages, entry]
}

// Never pass the error text through: it may carry technical server details.
export function friendlyErrorMessage(error: Error, online: boolean): string {
  if (!online || /Failed to fetch|NetworkError|Load failed/i.test(error.message)) {
    return m.home_error_offline()
  }
  return m.home_error_generic()
}
