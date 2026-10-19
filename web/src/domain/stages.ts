// Orchestrator technical names → what the person understands.
// The cascade names (stage_0…, visual_rag) are already here for when the
// backend starts emitting them (stage contract, plan item R5).
const STAGE_LABELS: Record<string, string> = {
  triage: 'Lendo a mensagem com atenção',
  image_extraction: 'Lendo o que está escrito no print',
  url_cascade: 'Investigando o link',
  stage_0_cache: 'Procurando em listas de golpes conhecidos',
  stage_1_signals: 'Vendo há quanto tempo o site existe',
  stage_2_inspection: 'Abrindo o site num lugar seguro, sem risco para você',
  visual_rag: 'Comparando com logotipos de bancos e lojas',
}

export function stageLabel(stage: string): string {
  return STAGE_LABELS[stage] ?? 'Conferindo mais um detalhe'
}
