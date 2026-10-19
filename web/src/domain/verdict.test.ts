import { describe, expect, it } from 'vitest'
import { m } from '../paraglide/messages.js'
import {
  channelLabel,
  familyAlertText,
  offersScamHelp,
  remainingExplanationsText,
  spokenVerdictText,
  todoTitle,
  verdictSteps,
  verdictSummary,
  verdictTitle,
} from './verdict'
import { VERDICT_MESSAGES, type ScanResponse, type ThreatLevel } from '../types'

const LEVELS: ThreatLevel[] = ['GOLPE', 'CUIDADO', 'SEGURO', 'INCONCLUSIVO']

const scam: ScanResponse = {
  id: 'scan-1',
  threat_level: 'GOLPE',
  verdict_message: 'scam_affective_coercion',
  details: { channel: 'texto', deciding_stage: 'triage', scores: {} },
}

describe('verdict copy', () => {
  it('gives every verdict level its own title', () => {
    const titles = LEVELS.map(verdictTitle)
    expect(new Set(titles).size).toBe(LEVELS.length)
    expect(verdictTitle('GOLPE')).toBe(m.verdict_title_scam())
  })

  it('frames the advice by urgency: scam and caution share "do it now"', () => {
    expect(todoTitle('GOLPE')).toBe(todoTitle('CUIDADO'))
    expect(todoTitle('SEGURO')).not.toBe(todoTitle('GOLPE'))
  })

  it('has a summary and at least one step for every message code the backend can send', () => {
    for (const code of VERDICT_MESSAGES) {
      expect(verdictSummary(code).length).toBeGreaterThan(10)
      expect(verdictSteps(code).length).toBeGreaterThan(0)
      for (const step of verdictSteps(code)) expect(step.length).toBeGreaterThan(5)
    }
  })

  it('offers scam help only when there is a risk of having been scammed', () => {
    expect(offersScamHelp('GOLPE')).toBe(true)
    expect(offersScamHelp('CUIDADO')).toBe(true)
    expect(offersScamHelp('SEGURO')).toBe(false)
    expect(offersScamHelp('INCONCLUSIVO')).toBe(false)
  })

  it('reads aloud title, summary, then the steps', () => {
    const [first, second] = verdictSteps('scam_affective_coercion')
    expect(spokenVerdictText(scam)).toBe(
      `${verdictTitle('GOLPE')} ${verdictSummary('scam_affective_coercion')} ${todoTitle('GOLPE')}: ${first} ${second}`
    )
  })

  it('builds the family alert in separate paragraphs', () => {
    const paragraphs = familyAlertText(scam).split('\n\n')
    expect(paragraphs[0]).toBe(m.verdict_family_alert_heading({ title: verdictTitle('GOLPE') }))
    expect(paragraphs[1]).toBe(verdictSummary('scam_affective_coercion'))
    expect(paragraphs[2].startsWith(todoTitle('GOLPE'))).toBe(true)
  })

  it('tells how many explanations are left today, with plural', () => {
    expect(remainingExplanationsText(2)).toBe('Você ainda pode pedir 2 explicações hoje.')
    expect(remainingExplanationsText(1)).toBe('Você ainda pode pedir 1 explicação hoje.')
    expect(remainingExplanationsText(0)).toBe(m.verdict_remaining_last())
  })

  it('describes each channel in everyday words', () => {
    expect(channelLabel('texto')).toBe(m.channel_text())
    expect(channelLabel('url')).toBe(m.channel_url())
    expect(channelLabel('imagem')).toBe(m.channel_image())
  })
})
