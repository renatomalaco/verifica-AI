import AxeBuilder from '@axe-core/playwright'
import type { Page } from '@playwright/test'
import { DEFAULT_PREFERENCES, SITUATIONS, preferencesFromSituations, type Preferences } from '../src/prefs/preferences'
import type { ScanResponse, StageEvent, ThreatLevel } from '../src/types'

export const WCAG_22_AA = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']

// Plain app, and the app with every situation of the accessibility catalog turned on.
export const MODES: Record<string, Preferences> = {
  default: DEFAULT_PREFERENCES,
  catalog: preferencesFromSituations(SITUATIONS.map((s) => s.id)),
}

/** Skips the first-visit tutorial and applies the given reading preferences before the app loads. */
export async function prepare(page: Page, prefs: Preferences = DEFAULT_PREFERENCES): Promise<void> {
  await page.addInitScript((stored) => {
    localStorage.setItem('vf.onboarded', '1')
    localStorage.setItem('vf.preferences', stored)
  }, JSON.stringify(prefs))
}

const MESSAGES: Record<ThreatLevel, ScanResponse['verdict_message']> = {
  GOLPE: 'scam_affective_coercion',
  CUIDADO: 'caution',
  SEGURO: 'safe',
  INCONCLUSIVO: 'inconclusive',
}

export function verdict(level: ThreatLevel, channel: ScanResponse['details']['channel'] = 'texto'): ScanResponse {
  return {
    id: `e2e-${level}`,
    threat_level: level,
    verdict_message: MESSAGES[level],
    details: { channel, deciding_stage: 'triage', scores: { is_phishing: 0.5 } },
  }
}

function sse(events: StageEvent[], response: ScanResponse): string {
  const stages = events.map((e) => `event: stage\ndata: ${JSON.stringify(e)}\n\n`).join('')
  return `${stages}event: verdict\ndata: ${JSON.stringify(response)}\n\n`
}

/** Answers the scan stream with the given verdict and returns what the app sent. */
export async function mockScan(page: Page, response: ScanResponse): Promise<() => Record<string, unknown>> {
  let sent: Record<string, unknown> = {}
  await page.route('**/api/v1/scans/stream', async (route) => {
    sent = route.request().postDataJSON()
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: sse([{ stage: 'triage', status: 'started' }, { stage: 'triage', status: 'done' }], response),
    })
  })
  return () => sent
}

/** The research area asks who is signed in; answer "nobody". */
export async function mockSignedOut(page: Page): Promise<void> {
  await page.route('**/api/v1/auth/**', (route) => route.fulfill({ status: 401, json: { detail: 'not_signed_in' } }))
}

// Contrast measured mid fade-in would be lower than what the person ends up reading.
async function settleAnimations(page: Page): Promise<void> {
  await page.evaluate(() =>
    Promise.all(
      document
        .getAnimations()
        .filter((a) => a.effect?.getComputedTiming().iterations !== Infinity)
        .map((a) => a.finished.catch(() => undefined))
    )
  )
}

export async function axeViolations(page: Page): Promise<string[]> {
  await settleAnimations(page)
  const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze()
  return results.violations.flatMap((v) => v.nodes.map((node) => `${v.id}: ${node.target.join(' ')}`))
}
