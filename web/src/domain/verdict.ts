// Verdict product rules: what to say and when. No React, testable in isolation.
import type { Channel, ScanResponse, ThreatLevel } from '../types'

const TITLES: Record<ThreatLevel, string> = {
  GOLPE: 'Isto é um golpe.',
  CUIDADO: 'Cuidado: pode ser golpe.',
  SEGURO: 'Nenhum sinal de golpe encontrado.',
  INCONCLUSIVO: 'Não deu para ter certeza.',
}

const TODO_TITLES: Record<ThreatLevel, string> = {
  GOLPE: 'Faça agora',
  CUIDADO: 'Faça agora',
  SEGURO: 'Mesmo assim',
  INCONCLUSIVO: 'Até ter certeza',
}

const CHANNEL_LABELS: Record<Channel, string> = {
  texto: 'mensagem de texto',
  url: 'link',
  imagem: 'foto ou print',
}

export const verdictTitle = (level: ThreatLevel): string => TITLES[level]

export const todoTitle = (level: ThreatLevel): string => TODO_TITLES[level]

export const channelLabel = (channel: Channel): string => CHANNEL_LABELS[channel]

// "Já caí nesse golpe" only makes sense when there was real risk.
export const offersScamHelp = (level: ThreatLevel): boolean => level === 'GOLPE' || level === 'CUIDADO'

// The backend sends guidance as running text; each sentence becomes a step.
export function adviceSteps(advice: string): string[] {
  return advice
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

export function spokenVerdictText({ threat_level, verdict_plain, action_advice }: ScanResponse): string {
  return `${verdictTitle(threat_level)} ${verdict_plain} ${todoTitle(threat_level)}: ${action_advice}`
}

export function familyAlertText({ threat_level, verdict_plain, action_advice }: ScanResponse): string {
  return [`Verifica: ${verdictTitle(threat_level)}`, verdict_plain, `${todoTitle(threat_level)}: ${action_advice}`].join('\n\n')
}

export function remainingExplanationsText(remaining: number): string {
  if (remaining <= 0) return 'Esta foi a última explicação de hoje.'
  return `Você ainda pode pedir ${remaining} ${remaining === 1 ? 'explicação' : 'explicações'} hoje.`
}
