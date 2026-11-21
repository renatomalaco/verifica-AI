import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  AccountError,
  RoleError,
  createInvite,
  createRole,
  disableAccount,
  listAccounts,
  listRoles,
  updateRole,
} from './researchAccounts'
import { SignedOutError } from './researchAuth'

const ACCOUNTS = [{ email: 'banca@exemplo.com', role: 'researcher', expires_at: null, status: 'invited' }]
const LINK = 'https://verifica.test/pesquisa/convite#token=abc'

function reply(status: number, body: unknown = {}) {
  return { ok: status < 400, status, json: async () => body, headers: new Headers() }
}

function mockFetch(...replies: ReturnType<typeof reply>[]) {
  const fn = vi.fn()
  replies.forEach((r) => fn.mockResolvedValueOnce(r))
  globalThis.fetch = fn
  return fn
}

describe('research accounts service', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('lists the accounts', async () => {
    mockFetch(reply(200, ACCOUNTS))
    expect(await listAccounts()).toEqual(ACCOUNTS)
  })

  it('sends the invite with the optional last day and returns the link', async () => {
    const fetchMock = mockFetch(reply(201, { url: LINK }))

    const url = await createInvite({ email: 'banca@exemplo.com', role: 'researcher', expiresOn: '2026-12-20' })

    expect(url).toBe(LINK)
    const [path, init] = fetchMock.mock.calls[0]
    expect(path).toBe('/api/v1/auth/invites')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ email: 'banca@exemplo.com', role: 'researcher', expires_on: '2026-12-20' })
  })

  it('sends no last day when access has no end', async () => {
    const fetchMock = mockFetch(reply(201, { url: LINK }))

    await createInvite({ email: 'banca@exemplo.com', role: 'admin', expiresOn: '' })

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ email: 'banca@exemplo.com', role: 'admin', expires_on: null })
  })

  it.each([
    [409, { detail: 'cannot_disable_self' }, 'self'],
    [404, { detail: 'account_not_found' }, 'not_found'],
    [500, {}, 'failed'],
  ])('turns a %i on blocking into a worded error', async (status, body, kind) => {
    mockFetch(reply(status, body))

    await expect(disableAccount('autor@exemplo.com')).rejects.toMatchObject(new AccountError(kind as AccountError['kind']))
  })

  it('blocks with a 204', async () => {
    const fetchMock = mockFetch(reply(204))

    await disableAccount('banca@exemplo.com')

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/auth/accounts/disable')
  })

  it('reports an ended session so the area goes back to sign-in', async () => {
    mockFetch(reply(401), reply(401))
    await expect(listAccounts()).rejects.toBeInstanceOf(SignedOutError)
  })

  it('lists the roles', async () => {
    const roles = [{ id: 'admin', name: 'Administrador', permissions: ['run_study', 'manage_access'] }]
    mockFetch(reply(200, roles))
    expect(await listRoles()).toEqual(roles)
  })

  it('creates a role and returns it', async () => {
    const created = { id: 'cargo-1', name: 'Orientador', permissions: ['run_study'] }
    const fetchMock = mockFetch(reply(201, created))

    expect(await createRole({ name: 'Orientador', permissions: ['run_study'] })).toEqual(created)
    const [path, init] = fetchMock.mock.calls[0]
    expect([path, init.method]).toEqual(['/api/v1/auth/roles', 'POST'])
  })

  it('saves a role with PUT on its id', async () => {
    const fetchMock = mockFetch(reply(200, { id: 'cargo-1', name: 'Banca', permissions: [] }))

    await updateRole('cargo-1', { name: 'Banca', permissions: [] })

    const [path, init] = fetchMock.mock.calls[0]
    expect([path, init.method]).toEqual(['/api/v1/auth/roles/cargo-1', 'PUT'])
    expect(JSON.parse(init.body)).toEqual({ name: 'Banca', permissions: [] })
  })

  it.each([
    [409, { detail: 'role_name_taken' }, 'name_taken'],
    [409, { detail: 'protected_role' }, 'protected'],
    [404, { detail: 'role_not_found' }, 'not_found'],
    [500, {}, 'failed'],
  ])('turns a %i on saving a role into a worded error', async (status, body, kind) => {
    mockFetch(reply(status, body))

    await expect(createRole({ name: 'X', permissions: [] })).rejects.toMatchObject(new RoleError(kind as RoleError['kind']))
  })
})
