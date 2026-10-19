import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from './App'
import * as api from './services/api'
import { buildConfigLink, DEFAULT_PREFERENCES } from './prefs/preferences'
import type { ScanResponse } from './types'
import { m } from './paraglide/messages.js'

const scam: ScanResponse = {
  id: 'app-1',
  threat_level: 'GOLPE',
  verdict_message: 'scam_affective_coercion',
  details: { channel: 'texto', deciding_stage: 'triage', scores: {} },
}

function skipOnboarding() {
  localStorage.setItem('vf.onboarded', '1')
}

describe('App', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
    window.history.pushState({}, '', '/')
    document.documentElement.removeAttribute('data-text-size')
  })

  it('asks who will use the app on the first visit and walks through the tutorial', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: m.onboarding_welcome_title() })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: m.onboarding_who_self() }))
    expect(screen.getByRole('heading', { name: 'Cole a mensagem que chegou' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: m.onboarding_tutorial_next() }))
    fireEvent.click(screen.getByRole('button', { name: m.onboarding_tutorial_next() }))
    fireEvent.click(screen.getByRole('button', { name: m.onboarding_tutorial_start() }))

    expect(screen.getByRole('heading', { name: m.home_title() })).toBeInTheDocument()
    expect(localStorage.getItem('vf.onboarded')).toBe('1')
  })

  it('does not show the tutorial again once the person has answered who will use it', () => {
    const first = render(<App />)
    fireEvent.click(screen.getByRole('button', { name: m.onboarding_who_self() }))
    first.unmount()

    render(<App />)
    expect(screen.getByRole('heading', { name: m.home_title() })).toBeInTheDocument()
  })

  it('reopens the tutorial on demand from the help button', () => {
    skipOnboarding()
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: m.common_how_to_use() }))
    expect(screen.getByRole('heading', { name: 'Cole a mensagem que chegou' })).toBeInTheDocument()
  })

  it('lets a family member pick situations and apply them on this phone', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: m.onboarding_who_someone_else() }))
    fireEvent.click(screen.getByRole('button', { name: new RegExp(m.settings_situation_vision_title()) }))
    fireEvent.click(screen.getByRole('button', { name: m.onboarding_catalog_apply() }))
    expect(document.documentElement.getAttribute('data-text-size')).toBe('large')
    expect(document.documentElement.getAttribute('data-contrast')).toBe('high')
  })

  it('applies settings received through a configuration link', () => {
    const link = buildConfigLink({ ...DEFAULT_PREFERENCES, textSize: 'xlarge' }, window.location.origin)
    window.history.pushState({}, '', new URL(link).pathname + new URL(link).hash)
    render(<App />)
    expect(screen.getByRole('status')).toHaveTextContent(m.common_config_applied())
    expect(document.documentElement.getAttribute('data-text-size')).toBe('xlarge')
    expect(screen.getByRole('heading', { name: 'Cole a mensagem que chegou' })).toBeInTheDocument()
    expect(window.location.hash).toBe('')
  })

  it('investigates and shows the verdict', async () => {
    skipOnboarding()
    vi.spyOn(api, 'scanStream').mockImplementation(async (_req, onStage, onVerdict) => {
      onStage({ stage: 'triage', status: 'started' })
      onStage({ stage: 'triage', status: 'done' })
      onVerdict(scam)
    })

    render(<App />)
    fireEvent.change(screen.getByLabelText(m.home_text_label()), { target: { value: 'Oi mãe, troquei de número' } })
    fireEvent.click(screen.getByRole('button', { name: 'Conferir agora' }))

    expect(await screen.findByRole('heading', { level: 1, name: m.verdict_title_scam() })).toBeInTheDocument()
    expect(screen.getByText('Oi mãe, troquei de número')).toBeInTheDocument()
    expect(api.scanStream).toHaveBeenCalledWith(
      { content: 'Oi mãe, troquei de número', image_b64: null },
      expect.any(Function),
      expect.any(Function),
      expect.any(Function),
      expect.any(AbortSignal)
    )
  })

  it('shows a friendly error without technical details', async () => {
    skipOnboarding()
    vi.spyOn(api, 'scanStream').mockImplementation(async (_req, _s, _v, onError) => {
      onError(new Error('Scanner connection error (500): Traceback ...'))
    })

    render(<App />)
    fireEvent.change(screen.getByLabelText(m.home_text_label()), { target: { value: 'teste' } })
    fireEvent.click(screen.getByRole('button', { name: 'Conferir agora' }))

    await waitFor(() => expect(screen.getByRole('heading', { name: m.common_error_title() })).toBeInTheDocument())
    expect(screen.queryByText(/Traceback/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: m.common_back() }))
    expect(screen.getByLabelText(m.home_text_label())).toHaveValue('teste')
  })

  it('cancels an investigation and goes back to the input', async () => {
    skipOnboarding()
    vi.spyOn(api, 'scanStream').mockImplementation(async (_req, onStage) => {
      onStage({ stage: 'triage', status: 'started' })
    })

    render(<App />)
    fireEvent.change(screen.getByLabelText(m.home_text_label()), { target: { value: 'teste' } })
    fireEvent.click(screen.getByRole('button', { name: 'Conferir agora' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Cancelar' }))
    expect(screen.getByRole('heading', { name: m.home_title() })).toBeInTheDocument()
  })

  it('prefills the link shared from another app', () => {
    skipOnboarding()
    window.history.pushState({}, '', '/?url=https%3A%2F%2Fgolpe.example')
    render(<App />)
    expect(screen.getByLabelText(m.home_url_label())).toHaveValue('https://golpe.example')
  })

  it('keeps the research area out of the public header', () => {
    skipOnboarding()
    render(<App />)
    expect(screen.queryByText(m.research_title())).not.toBeInTheDocument()
  })

  it('opens the protection course from the home screen and from its own address', () => {
    skipOnboarding()
    const first = render(<App />)
    fireEvent.click(screen.getAllByRole('button', { name: m.common_learn_protect() })[0])
    expect(screen.getByRole('heading', { level: 1, name: 'Aprenda a se proteger' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/aprender')
    first.unmount()

    render(<App />)
    expect(screen.getByRole('heading', { level: 1, name: 'Aprenda a se proteger' })).toBeInTheDocument()
  })

  it('links a scam verdict to the matching lesson', async () => {
    skipOnboarding()
    vi.spyOn(api, 'scanStream').mockImplementation(async (_req, _s, onVerdict) => {
      onVerdict({ ...scam, details: { ...scam.details, category: 'coercao_afetiva' } })
    })
    render(<App />)
    fireEvent.change(screen.getByLabelText(m.home_text_label()), { target: { value: 'Oi mãe' } })
    fireEvent.click(screen.getByRole('button', { name: 'Conferir agora' }))
    fireEvent.click(await screen.findByRole('button', { name: m.verdict_learn_scam() }))
    expect(screen.getByRole('heading', { level: 1, name: 'Golpe do falso parente' })).toBeInTheDocument()
  })

  it('explains anonymous data collection from the input screen', () => {
    skipOnboarding()
    render(<App />)
    expect(screen.getByText(m.home_privacy_note())).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Saiba como' }))
    expect(screen.getByRole('heading', { level: 1, name: 'Como o Verifica cuida dos seus dados' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/privacidade')
  })

  it('opens reading settings and changes the text size', () => {
    skipOnboarding()
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: m.common_reading_settings() }))
    fireEvent.click(screen.getByRole('radio', { name: 'Maior' }))
    expect(document.documentElement.getAttribute('data-text-size')).toBe('xlarge')
    fireEvent.click(screen.getByRole('switch', { name: new RegExp(m.settings_toggle_large_targets_title()) }))
    expect(document.documentElement.getAttribute('data-targets')).toBe('large')
  })
})
