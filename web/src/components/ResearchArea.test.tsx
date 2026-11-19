import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ResearchArea } from './ResearchArea'
import { m } from '../paraglide/messages.js'
import type { ResearchAccount, ResearchUser } from '../types'

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

  it('has no link to /metrics, which only the internal Prometheus reads now', async () => {
    serve({ ...signedOut, 'POST /api/v1/auth/login': { status: 200, body: RESEARCHER } })
    render(<ResearchArea onBack={vi.fn()} />)

    await signIn('banca@exemplo.com')

    const nav = await screen.findByRole('navigation', { name: m.research_nav_label() })
    const hrefs = Array.from(nav.querySelectorAll('a')).map((link) => link.getAttribute('href'))
    expect(hrefs).not.toContain('/metrics')
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

describe('ResearchArea accounts screen', () => {
  const BANCA: ResearchAccount = { ...RESEARCHER, status: 'active' }
  const ME: ResearchAccount = { ...ADMIN, status: 'active' }
  const LINK = 'https://verifica.test/pesquisa/convite#token=abc'

  afterEach(() => {
    vi.restoreAllMocks()
    window.history.replaceState(null, '', '/')
  })

  async function openAccounts(routes: Record<string, Route | Route[]>) {
    const fetchMock = serve({ 'GET /api/v1/auth/me': { status: 200, body: ADMIN }, ...routes })
    render(<ResearchArea onBack={vi.fn()} />)
    fireEvent.click(await screen.findByRole('link', { name: m.research_nav_accounts() }))
    return fetchMock
  }

  const blockButton = (email: string) => ({ name: m.research_accounts_block_label({ email }) })

  it('shows the accounts link only to the admin', async () => {
    serve({ 'GET /api/v1/auth/me': { status: 200, body: RESEARCHER } })
    render(<ResearchArea onBack={vi.fn()} />)

    await screen.findByRole('navigation', { name: m.research_nav_label() })
    expect(screen.queryByRole('link', { name: m.research_nav_accounts() })).not.toBeInTheDocument()
  })

  it('lists every account with its status', async () => {
    await openAccounts({ 'GET /api/v1/auth/accounts': { status: 200, body: [ME, { ...BANCA, status: 'invited' }] } })

    expect(await screen.findByRole('heading', { name: m.research_accounts_title() })).toBeInTheDocument()
    const row = (await screen.findByText('banca@exemplo.com')).closest('tr')!
    expect(within(row).getByText(m.research_status_invited())).toBeInTheDocument()
    expect(window.location.pathname).toBe('/pesquisa/contas')
  })

  it('generates an invite link that can be copied', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const fetchMock = await openAccounts({
      'GET /api/v1/auth/accounts': { status: 200, body: [ME] },
      'POST /api/v1/auth/invites': { status: 201, body: { url: LINK } },
    })

    fireEvent.change(await screen.findByLabelText(m.research_accounts_email()), { target: { value: 'banca@exemplo.com' } })
    fireEvent.change(screen.getByLabelText(m.research_accounts_last_day()), { target: { value: '2026-12-20' } })
    fireEvent.click(screen.getByRole('button', { name: m.research_accounts_invite_submit() }))

    expect(await screen.findByDisplayValue(LINK)).toBeInTheDocument()
    const [, init] = fetchMock.mock.calls.find(([path]) => path === '/api/v1/auth/invites')!
    expect(JSON.parse(init!.body as string)).toEqual({
      email: 'banca@exemplo.com',
      role: 'researcher',
      expires_on: '2026-12-20',
    })
    fireEvent.click(screen.getByRole('button', { name: m.research_accounts_copy() }))
    expect(await screen.findByText(m.research_accounts_copied())).toBeInTheDocument()
    expect(writeText).toHaveBeenCalledWith(LINK)
  })

  it('blocks another account after confirming, but never offers to block your own', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fetchMock = await openAccounts({
      'GET /api/v1/auth/accounts': [
        { status: 200, body: [ME, BANCA] },
        { status: 200, body: [ME, { ...BANCA, status: 'disabled' }] },
      ],
      'POST /api/v1/auth/accounts/disable': { status: 204 },
    })

    fireEvent.click(await screen.findByRole('button', blockButton('banca@exemplo.com')))

    const row = (await screen.findByText(m.research_status_disabled())).closest('tr')!
    expect(within(row).getByText('banca@exemplo.com')).toBeInTheDocument()
    expect(screen.queryByRole('button', blockButton(ADMIN.email))).not.toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/accounts/disable', expect.objectContaining({ method: 'POST' }))
  })

  it('keeps the account when blocking is not confirmed', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const fetchMock = await openAccounts({ 'GET /api/v1/auth/accounts': { status: 200, body: [ME, BANCA] } })

    fireEvent.click(await screen.findByRole('button', blockButton('banca@exemplo.com')))

    expect(fetchMock).not.toHaveBeenCalledWith('/api/v1/auth/accounts/disable', expect.anything())
  })

  it('words a failed invite', async () => {
    await openAccounts({
      'GET /api/v1/auth/accounts': { status: 200, body: [ME] },
      'POST /api/v1/auth/invites': { status: 500 },
    })

    fireEvent.change(await screen.findByLabelText(m.research_accounts_email()), { target: { value: 'banca@exemplo.com' } })
    fireEvent.click(screen.getByRole('button', { name: m.research_accounts_invite_submit() }))

    expect(await screen.findByRole('alert')).toHaveTextContent(m.research_accounts_invite_failed())
  })
})
