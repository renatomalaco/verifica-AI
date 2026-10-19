import { m } from '../paraglide/messages.js'

// Orchestrator technical names → what the person understands.
// The cascade names (stage_0…, visual_rag) are already here for when the
// backend starts emitting them (stage contract, plan item R5).
const STAGE_LABELS: Record<string, () => string> = {
  triage: m.home_stage_triage,
  image_extraction: m.home_stage_image_extraction,
  url_cascade: m.home_stage_url_cascade,
  stage_0_cache: m.home_stage_stage_0_cache,
  stage_1_signals: m.home_stage_stage_1_signals,
  stage_2_inspection: m.home_stage_stage_2_inspection,
  visual_rag: m.home_stage_visual_rag,
}

export function stageLabel(stage: string): string {
  return (STAGE_LABELS[stage] ?? m.home_stage_unknown)()
}
