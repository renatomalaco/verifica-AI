import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ResearchArea } from './ResearchArea'
import { m } from '../paraglide/messages.js'
import type { ResearchUser } from '../types'

const RESEARCHER: ResearchUser = { email: 'banca@exemplo.com', role: 'researcher', expires_at: null }
const ADMIN: ResearchUser = { email: 'autor@exemplo.com', role: 'admin', expires_at: null }

type Route = { status: number; body?: unknown; headers?: Record<string, string> }

// Answers by "METHOD path"; anything not listed is a 404 (e.g. no study run yet).
function serve(routes: Record<string, Route | Route[]>) {
  const queues = Object.fromEntries(Object.entries(routes).map(([k, v]) => [k, Array.isArray(v) ? [...v] : [v]]))
  const fetchMock = vi.fn(async (path: string, init?: RequestInit) => {
    const queue = queues[`${init?.method ?? 'GET'} ${path}`]
    const route = (queue && (queue.length > 1 ? queue.shift() : queue[0])) ?? { status: 404 }
    return {
      ok: route.status < 400,
      status: route.status,
      json: async () => route.body ?? {},
      headers: new Headers(route.headers ?? {}),
    }
  })
  global.fetch = fetchMock as unknown as typeof fetch
  return fetchMock
}

const signedOut = { 'GET /api/v1/auth/me': { status: 401 }, 'POST /api/v1/auth/refresh': { status: 401 } }

async function signIn(email: string, password = 'senha-da-banca-2026') {
  fireEvent.change(await screen.findByLabelText(m.research_login_email()), { target: { value: email } })
  fireEvent.change(screen.getByLabelText(m.research_login_password()), { target: { value: password } })
  fireEvent.click(screen.getByRole('button', { name: m.research_login_submit() }))
}

describe('ResearchArea', () => {
  afterEach(() => vi.restoreAllMocks())

  it('asks to sign in and shows no research data without an account', async () => {
    serve(signedOut)
    render(<ResearchArea onBack={vi.fn()} />)

    expect(await screen.findByRole('heading', { name: m.research_login_title() })).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: m.research_nav_label() })).not.toBeInTheDocument()
    expect(screen.queryByText(m.research_title())).not.toBeInTheDocument()
  })

  it('opens the side navigation and the report after signing in', async () => {
    serve({ ...signedOut, 'POST /api/v1/auth/login': { status: 200, body: RESEARCHER } })
    render(<ResearchArea onBack={vi.fn()} />)

    await signIn('banca@exemplo.com')

    expect(await screen.findByRole('navigation', { name: m.research_nav_label() })).toBeInTheDocument()
    expect(screen.getByText(m.research_nav_signed_in_as({ email: 'banca@exemplo.com' }))).toBeInTheDocument()
    expect(await screen.findByText(m.research_missing_title())).toBeInTheDocument()
  })

  it('shows a generic message for wrong credentials', async () => {
    serve({ ...signedOut, 'POST /api/v1/auth/login': { status: 401, body: { detail: 'invalid_credentials' } } })
    render(<ResearchArea onBack={vi.fn()} />)

    await signIn('banca@exemplo.com', 'senha-errada-qualquer')

    expect(await screen.findByRole('alert')).toHaveTextContent(m.research_login_invalid())
  })

  it('tells how long to wait after too many attempts', async () => {
    serve({ ...signedOut, 'POST /api/v1/auth/login': { status: 429, headers: { 'Retry-After': '900' } } })
    render(<ResearchArea onBack={vi.fn()} />)

    await signIn('banca@exemplo.com')

    expect(await screen.findByRole('alert')).toHaveTextContent(m.research_login_throttled({ minutes: 15 }))
  })

  it('hides the run button from researchers', async () => {
    serve({ 'GET /api/v1/auth/me': { status: 200, body: RESEARCHER } })
    render(<ResearchArea onBack={vi.fn()} />)

    await screen.findByRole('navigation', { name: m.research_nav_label() })
    expect(screen.queryByRole('button', { name: m.research_nav_run() })).not.toBeInTheDocument()
  })

  it('lets the admin run the study', async () => {
    const fetchMock = serve({
      'GET /api/v1/auth/me': { status: 200, body: ADMIN },
      'POST /pesquisa/run': { status: 200, body: { modes: [] } },
    })
    render(<ResearchArea onBack={vi.fn()} />)

    fireEvent.click(await screen.findByRole('button', { name: m.research_nav_run() }))

    expect(await screen.findByText(m.research_nav_run_done())).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('/pesquisa/run', expect.objectContaining({ method: 'POST' }))
  })

  it('signs out and goes back to the sign-in screen', async () => {
    const fetchMock = serve({
      'GET /api/v1/auth/me': { status: 200, body: RESEARCHER },
      'DELETE /api/v1/auth/refresh': { status: 204 },
    })
    render(<ResearchArea onBack={vi.fn()} />)

    fireEvent.click(await screen.findByRole('button', { name: m.research_nav_sign_out() }))

    expect(await screen.findByRole('heading', { name: m.research_login_title() })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/refresh', expect.objectContaining({ method: 'DELETE' }))
  })

  it('returns to sign-in when the session ends while reading the report', async () => {
    serve({
      'GET /api/v1/auth/me': { status: 200, body: RESEARCHER },
      'GET /pesquisa/report': { status: 401 },
      'POST /api/v1/auth/refresh': { status: 401 },
    })
    render(<ResearchArea onBack={vi.fn()} />)

    expect(await screen.findByRole('heading', { name: m.research_login_title() })).toBeInTheDocument()
  })
})
