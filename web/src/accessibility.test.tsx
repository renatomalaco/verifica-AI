import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { m } from './paraglide/messages.js'
import { DEFAULT_PREFERENCES, SITUATIONS, preferencesFromSituations } from './prefs/preferences'
import * as api from './services/api'
import { axeViolations } from './testing/axe'
import type { ScanResponse, ThreatLevel } from './types'

// Accessibility is optional for the person (situation catalog), but the markup must be clean
// in both modes: plain, and with every situation of the catalog turned on.
const MODES = {
  default: DEFAULT_PREFERENCES,
  catalog: preferencesFromSituations(SITUATIONS.map((s) => s.id)),
}

const VERDICTS: Record<ThreatLevel, { message: ScanResponse['verdict_message']; title: () => string }> = {
  GOLPE: { message: 'scam_affective_coercion', title: m.verdict_title_scam },
  CUIDADO: { message: 'caution', title: m.verdict_title_caution },
  SEGURO: { message: 'safe', title: m.verdict_title_safe },
  INCONCLUSIVO: { message: 'inconclusive', title: m.verdict_title_inconclusive },
}

function openAt(path: string, onboarded = true) {
  window.history.pushState({}, '', path)
  if (onboarded) localStorage.setItem('vf.onboarded', '1')
  return render(<App />)
}

async function investigate(level: ThreatLevel) {
  vi.spyOn(api, 'scanStream').mockImplementation(async (_req, onStage, onVerdict) => {
    onStage({ stage: 'triage', status: 'done' })
    onVerdict({
      id: `a11y-${level}`,
      threat_level: level,
      verdict_message: VERDICTS[level].message,
      details: { channel: 'texto', deciding_stage: 'triage', scores: { is_phishing: 0.5 } },
    })
  })
  openAt('/')
  fireEvent.change(screen.getByLabelText(m.home_text_label()), { target: { value: 'Oi mãe, troquei de número' } })
  fireEvent.click(screen.getByRole('button', { name: 'Conferir agora' }))
  await screen.findByRole('heading', { level: 1, name: VERDICTS[level].title() })
}

// The research area checks the session first; answer "signed out" so the sign-in screen shows.
function signedOutServer() {
  global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({}), headers: new Headers() })
}

describe.each(Object.entries(MODES))('accessibility (%s mode)', (_mode, prefs) => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('vf.preferences', JSON.stringify(prefs))
  })

  afterEach(() => vi.restoreAllMocks())

  it('welcome screen', async () => {
    openAt('/', false)
    expect(await axeViolations()).toEqual([])
  })

  it('tutorial', async () => {
    openAt('/')
    fireEvent.click(screen.getByRole('button', { name: m.common_how_to_use() }))
    expect(await axeViolations()).toEqual([])
  })

  it('home (input)', async () => {
    openAt('/')
    expect(await axeViolations()).toEqual([])
  })

  it.each(Object.keys(VERDICTS) as ThreatLevel[])('verdict %s', async (level) => {
    await investigate(level)
    expect(await axeViolations()).toEqual([])
  })

  it('reading settings', async () => {
    openAt('/')
    fireEvent.click(screen.getByRole('button', { name: m.common_reading_settings() }))
    expect(await axeViolations()).toEqual([])
  })

  it('protection course', async () => {
    openAt('/aprender')
    expect(await axeViolations()).toEqual([])
  })

  it('privacy page', async () => {
    openAt('/privacidade')
    expect(await axeViolations()).toEqual([])
  })

  it('research sign-in', async () => {
    signedOutServer()
    openAt('/pesquisa')
    await screen.findByRole('heading', { name: m.research_login_title() })
    expect(await axeViolations()).toEqual([])
  })

  it('research invite', async () => {
    openAt('/pesquisa/convite#token=convite-123')
    expect(await axeViolations()).toEqual([])
  })
})
