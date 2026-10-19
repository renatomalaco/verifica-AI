import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { VerdictCard } from './VerdictCard'
import { verdictSteps } from '../domain/verdict'
import { PreferencesProvider } from '../prefs/PreferencesProvider'
import { DEFAULT_PREFERENCES, savePreferences } from '../prefs/preferences'
import type { ScanResponse } from '../types'
import type { EvidenceData } from '../domain/investigation'
import { m } from '../paraglide/messages.js'

const scam: ScanResponse = {
  id: 'scan-1',
  threat_level: 'GOLPE',
  verdict_message: 'scam_affective_coercion',
  details: { channel: 'texto', deciding_stage: 'triage', scores: { jev: 0.97 } },
}

const evidence: EvidenceData = { tab: 'text', content: 'Oi mãe, troquei de número', imageB64: null }

function renderCard(response: ScanResponse = scam, onReset = () => {}) {
  return render(
    <PreferencesProvider>
      <VerdictCard response={response} evidence={evidence} onReset={onReset} />
    </PreferencesProvider>
  )
}

describe('VerdictCard', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('shows the verdict, the evidence and the advice as numbered steps', () => {
    renderCard()
    expect(screen.getByRole('heading', { level: 1, name: m.verdict_title_scam() })).toHaveFocus()
    expect(screen.getByText('Oi mãe, troquei de número')).toBeInTheDocument()
    const steps = screen.getAllByRole('listitem')
    expect(steps).toHaveLength(2)
    expect(steps[0]).toHaveTextContent(verdictSteps('scam_affective_coercion')[0])
  })

  it('uses honest wording for an inconclusive result', () => {
    renderCard({ ...scam, threat_level: 'INCONCLUSIVO' })
    expect(screen.getByRole('heading', { level: 1, name: m.verdict_title_inconclusive() })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: m.verdict_todo_inconclusive() })).toBeInTheDocument()
    expect(screen.queryByText(m.verdict_scam_help_toggle())).not.toBeInTheDocument()
  })

  it('explains when the detailed explanation is not available yet', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({}) })
    renderCard()
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: m.verdict_explain() }))
    })
    expect(await screen.findByText(m.verdict_explanation_unavailable())).toBeInTheDocument()
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/scans/scan-1/explain', expect.objectContaining({ method: 'POST' }))
  })

  it('tells the person when the daily explanation quota is over', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 429, json: async () => ({ retry_at: null }) })
    renderCard()
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: m.verdict_explain() }))
    })
    expect(await screen.findByText(m.verdict_explanation_quota({ returns: m.verdict_explanation_returns_tomorrow() }))).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: m.verdict_title_scam() })).toBeInTheDocument()
  })

  it('shows the explanation lines and the remaining quota', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ lines: ['A mensagem pede dinheiro com pressa.'], remaining_today: 2 }),
    })
    renderCard()
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: m.verdict_explain() }))
    })
    expect(await screen.findByText('A mensagem pede dinheiro com pressa.')).toBeInTheDocument()
    expect(screen.getByText(m.verdict_remaining({ count: 2 }))).toBeInTheDocument()
  })

  it('opens the "what if I already fell for it" help', () => {
    renderCard()
    const toggle = screen.getByRole('button', { name: m.verdict_scam_help_toggle() })
    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText(m.verdict_scam_help_report_strong())).toBeInTheDocument()
  })

  it('hides extras in simple mode', () => {
    savePreferences({ ...DEFAULT_PREFERENCES, simpleMode: true })
    renderCard()
    expect(screen.queryByRole('button', { name: m.verdict_explain() })).not.toBeInTheDocument()
    expect(screen.queryByText(m.verdict_tech_summary())).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: m.verdict_listen() })).toBeInTheDocument()
  })

  it('calls onReset from the back button', () => {
    const onReset = vi.fn()
    renderCard(scam, onReset)
    fireEvent.click(screen.getByRole('button', { name: m.verdict_check_another() }))
    expect(onReset).toHaveBeenCalledTimes(1)
  })
})
