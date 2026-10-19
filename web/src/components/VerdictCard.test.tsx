import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { VerdictCard } from './VerdictCard'
import { PreferencesProvider } from '../prefs/PreferencesProvider'
import { DEFAULT_PREFERENCES, savePreferences } from '../prefs/preferences'
import type { ScanResponse } from '../types'
import type { EvidenceData } from '../domain/investigation'

const scam: ScanResponse = {
  id: 'scan-1',
  threat_level: 'GOLPE',
  verdict_plain: 'Alguém está fingindo ser da sua família para pedir dinheiro.',
  action_advice: 'Não mande Pix nem dinheiro. Ligue para o seu filho no número que você já tem salvo.',
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
    expect(screen.getByRole('heading', { level: 1, name: 'Isto é um golpe.' })).toHaveFocus()
    expect(screen.getByText('Oi mãe, troquei de número')).toBeInTheDocument()
    const steps = screen.getAllByRole('listitem')
    expect(steps).toHaveLength(2)
    expect(steps[0]).toHaveTextContent('Não mande Pix nem dinheiro.')
  })

  it('uses honest wording for an inconclusive result', () => {
    renderCard({ ...scam, threat_level: 'INCONCLUSIVO' })
    expect(screen.getByRole('heading', { level: 1, name: 'Não deu para ter certeza.' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Até ter certeza' })).toBeInTheDocument()
    expect(screen.queryByText(/Já caí nesse golpe/)).not.toBeInTheDocument()
  })

  it('explains when the detailed explanation is not available yet', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({}) })
    renderCard()
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Me explica' }))
    })
    expect(await screen.findByText(/ainda não está disponível/)).toBeInTheDocument()
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/scans/scan-1/explain', expect.objectContaining({ method: 'POST' }))
  })

  it('tells the person when the daily explanation quota is over', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 429, json: async () => ({ retry_at: null }) })
    renderCard()
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Me explica' }))
    })
    expect(await screen.findByText(/já usou as explicações de hoje/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'Isto é um golpe.' })).toBeInTheDocument()
  })

  it('shows the explanation lines and the remaining quota', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ lines: ['A mensagem pede dinheiro com pressa.'], remaining_today: 2 }),
    })
    renderCard()
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Me explica' }))
    })
    expect(await screen.findByText('A mensagem pede dinheiro com pressa.')).toBeInTheDocument()
    expect(screen.getByText(/ainda pode pedir 2 explicações/)).toBeInTheDocument()
  })

  it('opens the "what if I already fell for it" help', () => {
    renderCard()
    const toggle = screen.getByRole('button', { name: /Já caí nesse golpe/ })
    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText(/Registre um boletim de ocorrência/)).toBeInTheDocument()
  })

  it('hides extras in simple mode', () => {
    savePreferences({ ...DEFAULT_PREFERENCES, simpleMode: true })
    renderCard()
    expect(screen.queryByRole('button', { name: 'Me explica' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Ver detalhes da investigação/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Ouvir/ })).toBeInTheDocument()
  })

  it('calls onReset from the back button', () => {
    const onReset = vi.fn()
    renderCard(scam, onReset)
    fireEvent.click(screen.getByRole('button', { name: /Conferir outra/ }))
    expect(onReset).toHaveBeenCalledTimes(1)
  })
})
