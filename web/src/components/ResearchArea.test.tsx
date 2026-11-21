import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ResearchArea } from './ResearchArea'
import { m } from '../paraglide/messages.js'
import type { ResearchAccount, ResearchRole, ResearchUser } from '../types'

const ADMIN_ROLE: ResearchRole = { id: 'admin', name: 'Administrador', permissions: ['run_study', 'manage_access'] }
const RESEARCHER_ROLE: ResearchRole = { id: 'researcher', name: 'Pesquisador', permissions: [] }
const ROLES = [ADMIN_ROLE, RESEARCHER_ROLE]
const RESEARCHER: ResearchUser = { email: 'banca@exemplo.com', role: RESEARCHER_ROLE, expires_at: null }
const ADMIN: ResearchUser = { email: 'autor@exemplo.com', role: ADMIN_ROLE, expires_at: null }

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
    const fetchMock = serve({
      'GET /api/v1/auth/me': { status: 200, body: ADMIN },
      'GET /api/v1/auth/roles': { status: 200, body: ROLES },
      ...routes,
    })
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

describe('ResearchArea roles', () => {
  const ORIENTADOR: ResearchRole = { id: 'cargo-1', name: 'Orientador', permissions: ['run_study'] }

  afterEach(() => {
    vi.restoreAllMocks()
    window.history.replaceState(null, '', '/')
  })

  async function openRoles(routes: Record<string, Route | Route[]> = {}) {
    const fetchMock = serve({
      'GET /api/v1/auth/me': { status: 200, body: ADMIN },
      'GET /api/v1/auth/accounts': { status: 200, body: [] },
      'GET /api/v1/auth/roles': { status: 200, body: ROLES },
      ...routes,
    })
    render(<ResearchArea onBack={vi.fn()} />)
    fireEvent.click(await screen.findByRole('link', { name: m.research_nav_accounts() }))
    await screen.findByRole('heading', { name: m.research_roles_title() })
    return fetchMock
  }

  const roleForm = (name: string) => screen.findByRole('form', { name: m.research_roles_edit_label({ name }) })
  const body = (fetchMock: ReturnType<typeof serve>, key: string) => {
    const [, init] = fetchMock.mock.calls.find(([path, i]) => `${i?.method ?? 'GET'} ${path}` === key)!
    return JSON.parse(init!.body as string)
  }

  it('creates a role with a name and the permissions ticked', async () => {
    const fetchMock = await openRoles({
      'POST /api/v1/auth/roles': { status: 201, body: ORIENTADOR },
      'GET /api/v1/auth/roles': [
        { status: 200, body: ROLES },
        { status: 200, body: [...ROLES, ORIENTADOR] },
      ],
    })
    const form = screen.getByRole('form', { name: m.research_roles_new_title() })

    fireEvent.change(within(form).getByLabelText(m.research_roles_name()), { target: { value: 'Orientador' } })
    fireEvent.click(within(form).getByLabelText(m.research_permission_run_study()))
    fireEvent.click(within(form).getByRole('button', { name: m.research_roles_create() }))

    expect(await roleForm('Orientador')).toBeInTheDocument()
    expect(body(fetchMock, 'POST /api/v1/auth/roles')).toEqual({ name: 'Orientador', permissions: ['run_study'] })
  })

  it('renames a role and changes its permissions', async () => {
    const fetchMock = await openRoles({
      'PUT /api/v1/auth/roles/researcher': {
        status: 200,
        body: { id: 'researcher', name: 'Banca', permissions: ['run_study'] },
      },
    })
    const form = await roleForm('Pesquisador')

    fireEvent.change(within(form).getByLabelText(m.research_roles_name()), { target: { value: 'Banca' } })
    fireEvent.click(within(form).getByLabelText(m.research_permission_run_study()))
    fireEvent.click(within(form).getByRole('button', { name: m.research_roles_save() }))

    expect(await within(form).findByText(m.research_roles_saved())).toBeInTheDocument()
    expect(body(fetchMock, 'PUT /api/v1/auth/roles/researcher')).toEqual({ name: 'Banca', permissions: ['run_study'] })
  })

  it('keeps access management ticked and locked on the admin role', async () => {
    await openRoles()
    const form = await roleForm('Administrador')

    const manage = within(form).getByLabelText(m.research_permission_manage_access())
    expect(manage).toBeChecked()
    expect(manage).toBeDisabled()
  })

  it('words a role name that is already taken', async () => {
    await openRoles({ 'POST /api/v1/auth/roles': { status: 409, body: { detail: 'role_name_taken' } } })
    const form = screen.getByRole('form', { name: m.research_roles_new_title() })

    fireEvent.change(within(form).getByLabelText(m.research_roles_name()), { target: { value: 'pesquisador' } })
    fireEvent.click(within(form).getByRole('button', { name: m.research_roles_create() }))

    expect(await within(form).findByRole('alert')).toHaveTextContent(m.research_roles_name_taken())
  })

  it('offers every role when inviting someone', async () => {
    await openRoles({ 'GET /api/v1/auth/roles': { status: 200, body: [...ROLES, ORIENTADOR] } })

    const picker = await screen.findByLabelText(m.research_accounts_role())
    await within(picker).findByRole('option', { name: 'Orientador' })
    expect(within(picker).getAllByRole('option').map((o) => o.textContent)).toEqual([
      'Administrador',
      'Pesquisador',
      'Orientador',
    ])
  })
})
