import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from './App'
import * as api from './services/api'
import { buildConfigLink, DEFAULT_PREFERENCES } from './prefs/preferences'
import type { ScanResponse } from './types'

const scam: ScanResponse = {
  id: 'app-1',
  threat_level: 'GOLPE',
  verdict_plain: 'Alguém está fingindo ser da sua família.',
  action_advice: 'Não mande Pix. Ligue para o seu filho.',
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
    expect(screen.getByRole('heading', { name: /Confira antes de responder/ })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Eu mesmo' }))
    expect(screen.getByRole('heading', { name: 'Cole a mensagem que chegou' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Próximo' }))
    fireEvent.click(screen.getByRole('button', { name: 'Próximo' }))
    fireEvent.click(screen.getByRole('button', { name: 'Começar' }))

    expect(screen.getByRole('heading', { name: 'O que chegou para você?' })).toBeInTheDocument()
    expect(localStorage.getItem('vf.onboarded')).toBe('1')
  })

  it('does not show the tutorial again once the person has answered who will use it', () => {
    const first = render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Eu mesmo' }))
    first.unmount()

    render(<App />)
    expect(screen.getByRole('heading', { name: 'O que chegou para você?' })).toBeInTheDocument()
  })

  it('reopens the tutorial on demand from the help button', () => {
    skipOnboarding()
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Como usar' }))
    expect(screen.getByRole('heading', { name: 'Cole a mensagem que chegou' })).toBeInTheDocument()
  })

  it('lets a family member pick situations and apply them on this phone', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Vou configurar para alguém' }))
    fireEvent.click(screen.getByRole('button', { name: /Catarata ou baixa visão/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Aplicar neste aparelho' }))
    expect(document.documentElement.getAttribute('data-text-size')).toBe('large')
    expect(document.documentElement.getAttribute('data-contrast')).toBe('high')
  })

  it('applies settings received through a configuration link', () => {
    const link = buildConfigLink({ ...DEFAULT_PREFERENCES, textSize: 'xlarge' }, window.location.origin)
    window.history.pushState({}, '', new URL(link).pathname + new URL(link).hash)
    render(<App />)
    expect(screen.getByRole('status')).toHaveTextContent('Ajustes aplicados')
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
    fireEvent.change(screen.getByLabelText('Cole a mensagem que você recebeu'), { target: { value: 'Oi mãe, troquei de número' } })
    fireEvent.click(screen.getByRole('button', { name: 'Conferir agora' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Isto é um golpe.' })).toBeInTheDocument()
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
      onError(new Error('Erro na conexão com o scanner (500): Traceback ...'))
    })

    render(<App />)
    fireEvent.change(screen.getByLabelText('Cole a mensagem que você recebeu'), { target: { value: 'teste' } })
    fireEvent.click(screen.getByRole('button', { name: 'Conferir agora' }))

    await waitFor(() => expect(screen.getByRole('heading', { name: /A investigação não terminou/ })).toBeInTheDocument())
    expect(screen.queryByText(/Traceback/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Voltar' }))
    expect(screen.getByLabelText('Cole a mensagem que você recebeu')).toHaveValue('teste')
  })

  it('cancels an investigation and goes back to the input', async () => {
    skipOnboarding()
    vi.spyOn(api, 'scanStream').mockImplementation(async (_req, onStage) => {
      onStage({ stage: 'triage', status: 'started' })
    })

    render(<App />)
    fireEvent.change(screen.getByLabelText('Cole a mensagem que você recebeu'), { target: { value: 'teste' } })
    fireEvent.click(screen.getByRole('button', { name: 'Conferir agora' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Cancelar' }))
    expect(screen.getByRole('heading', { name: 'O que chegou para você?' })).toBeInTheDocument()
  })

  it('prefills the link shared from another app', () => {
    skipOnboarding()
    window.history.pushState({}, '', '/?url=https%3A%2F%2Fgolpe.example')
    render(<App />)
    expect(screen.getByLabelText('Cole o endereço do site')).toHaveValue('https://golpe.example')
  })

  it('keeps the research area out of the public header', () => {
    skipOnboarding()
    render(<App />)
    expect(screen.queryByText(/Ablação/)).not.toBeInTheDocument()
  })

  it('opens the protection course from the home screen and from its own address', () => {
    skipOnboarding()
    const first = render(<App />)
    fireEvent.click(screen.getAllByRole('button', { name: 'Aprenda a se proteger' })[0])
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
    fireEvent.change(screen.getByLabelText('Cole a mensagem que você recebeu'), { target: { value: 'Oi mãe' } })
    fireEvent.click(screen.getByRole('button', { name: 'Conferir agora' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Aprenda a reconhecer esse tipo de golpe' }))
    expect(screen.getByRole('heading', { level: 1, name: 'Golpe do falso parente' })).toBeInTheDocument()
  })

  it('explains anonymous data collection from the input screen', () => {
    skipOnboarding()
    render(<App />)
    expect(screen.getByText(/Só registra dados anônimos para a pesquisa/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Saiba como' }))
    expect(screen.getByRole('heading', { level: 1, name: 'Como o Verifica cuida dos seus dados' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/privacidade')
  })

  it('opens reading settings and changes the text size', () => {
    skipOnboarding()
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Ajustes de leitura' }))
    fireEvent.click(screen.getByRole('radio', { name: 'Maior' }))
    expect(document.documentElement.getAttribute('data-text-size')).toBe('xlarge')
    fireEvent.click(screen.getByRole('switch', { name: /Botões maiores/ }))
    expect(document.documentElement.getAttribute('data-targets')).toBe('large')
  })
})
