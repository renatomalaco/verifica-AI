// Verdict product rules: what to say and when. No React, testable in isolation.
import { m } from '../paraglide/messages.js'
import type { Channel, ScanResponse, ThreatLevel, VerdictMessage } from '../types'

type Text = () => string

const TITLES: Record<ThreatLevel, Text> = {
  GOLPE: m.verdict_title_scam,
  CUIDADO: m.verdict_title_caution,
  SEGURO: m.verdict_title_safe,
  INCONCLUSIVO: m.verdict_title_inconclusive,
}

const TODO_TITLES: Record<ThreatLevel, Text> = {
  GOLPE: m.verdict_todo_scam,
  CUIDADO: m.verdict_todo_caution,
  SEGURO: m.verdict_todo_safe,
  INCONCLUSIVO: m.verdict_todo_inconclusive,
}

const CHANNEL_LABELS: Record<Channel, Text> = {
  texto: m.channel_text,
  url: m.channel_url,
  imagem: m.channel_image,
}

// Functions, not strings, so the wording follows the locale at call time.
const MESSAGES: Record<VerdictMessage, { summary: Text; steps: Text[] }> = {
  scam_affective_coercion: {
    summary: m.verdict_scam_affective_coercion_summary,
    steps: [m.verdict_scam_affective_coercion_step_1, m.verdict_scam_affective_coercion_step_2],
  },
  scam_financial_threat: {
    summary: m.verdict_scam_financial_threat_summary,
    steps: [m.verdict_scam_financial_threat_step_1, m.verdict_scam_financial_threat_step_2],
  },
  scam_urgency: {
    summary: m.verdict_scam_urgency_summary,
    steps: [m.verdict_scam_urgency_step_1, m.verdict_scam_urgency_step_2],
  },
  scam_brand_spoofing: {
    summary: m.verdict_scam_brand_spoofing_summary,
    steps: [m.verdict_scam_brand_spoofing_step_1, m.verdict_scam_brand_spoofing_step_2],
  },
  scam_generic: {
    summary: m.verdict_scam_generic_summary,
    steps: [m.verdict_scam_generic_step_1, m.verdict_scam_generic_step_2],
  },
  caution: {
    summary: m.verdict_caution_summary,
    steps: [m.verdict_caution_step_1, m.verdict_caution_step_2],
  },
  safe: {
    summary: m.verdict_safe_summary,
    steps: [m.verdict_safe_step_1],
  },
  inconclusive: {
    summary: m.verdict_inconclusive_summary,
    steps: [m.verdict_inconclusive_step_1, m.verdict_inconclusive_step_2],
  },
}

export const verdictTitle = (level: ThreatLevel): string => TITLES[level]()

export const todoTitle = (level: ThreatLevel): string => TODO_TITLES[level]()

export const channelLabel = (channel: Channel): string => CHANNEL_LABELS[channel]()

export const verdictSummary = (code: VerdictMessage): string => MESSAGES[code].summary()

export const verdictSteps = (code: VerdictMessage): string[] => MESSAGES[code].steps.map((step) => step())

// "Já caí nesse golpe" only makes sense when there was real risk.
export const offersScamHelp = (level: ThreatLevel): boolean => level === 'GOLPE' || level === 'CUIDADO'

export function spokenVerdictText({ threat_level, verdict_message }: ScanResponse): string {
  const steps = verdictSteps(verdict_message).join(' ')
  return `${verdictTitle(threat_level)} ${verdictSummary(verdict_message)} ${todoTitle(threat_level)}: ${steps}`
}

export function familyAlertText({ threat_level, verdict_message }: ScanResponse): string {
  const steps = verdictSteps(verdict_message).join(' ')
  return [
    m.verdict_family_alert_heading({ title: verdictTitle(threat_level) }),
    verdictSummary(verdict_message),
    `${todoTitle(threat_level)}: ${steps}`,
  ].join('\n\n')
}

export function remainingExplanationsText(remaining: number): string {
  if (remaining <= 0) return m.verdict_remaining_last()
  return m.verdict_remaining({ count: remaining })
}
