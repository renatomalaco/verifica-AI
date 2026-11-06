import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  InviteError,
  LoginError,
  SignedOutError,
  acceptInvite,
  fetchCurrentUser,
  login,
  logout,
  researchFetch,
} from './researchAuth'

const USER = { email: 'banca@exemplo.com', role: 'researcher', expires_at: null }

function reply(status: number, body: unknown = {}, headers: Record<string, string> = {}) {
  return { ok: status < 400, status, json: async () => body, headers: new Headers(headers) }
}

function mockFetch(...replies: ReturnType<typeof reply>[]) {
  const fn = vi.fn()
  replies.forEach((r) => fn.mockResolvedValueOnce(r))
  globalThis.fetch = fn
  return fn
}

describe('research sign-in service', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('returns the signed-in user', async () => {
    mockFetch(reply(200, USER))
    expect(await fetchCurrentUser()).toEqual(USER)
  })

  it('renews the 15-minute access once and retries', async () => {
    const fetchMock = mockFetch(reply(401), reply(200, USER), reply(200, USER))

    expect(await fetchCurrentUser()).toEqual(USER)
    expect(fetchMock.mock.calls.map((c) => [c[0], c[1]?.method ?? 'GET'])).toEqual([
      ['/api/v1/auth/me', 'GET'],
      ['/api/v1/auth/refresh', 'POST'],
      ['/api/v1/auth/me', 'GET'],
    ])
  })

  it('is signed out when the refresh is refused', async () => {
    mockFetch(reply(401), reply(401))
    expect(await fetchCurrentUser()).toBeNull()
  })

  it('renews only once when several calls expire together', async () => {
    // Two rotations would look like a reused token and end the session.
    let renewed = false
    const fetchMock = vi.fn(async (url: string) => {
      if (url === '/api/v1/auth/refresh') {
        renewed = true
        return reply(200, USER)
      }
      return reply(renewed ? 200 : 401)
    })
    globalThis.fetch = fetchMock as unknown as typeof fetch

    await Promise.all([researchFetch('/pesquisa/report'), researchFetch('/pesquisa/report')])

    expect(fetchMock.mock.calls.filter((c) => c[0] === '/api/v1/auth/refresh')).toHaveLength(1)
  })

  it('throws SignedOutError when the retry is still unauthorized', async () => {
    mockFetch(reply(401), reply(200, USER), reply(401))
    await expect(researchFetch('/pesquisa/report')).rejects.toBeInstanceOf(SignedOutError)
  })

  it('logs in with the e-mail and password', async () => {
    const fetchMock = mockFetch(reply(200, USER))

    expect(await login('banca@exemplo.com', 'senha-da-banca-2026')).toEqual(USER)
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      email: 'banca@exemplo.com',
      password: 'senha-da-banca-2026',
    })
  })

  it.each([
    [reply(401, { detail: 'invalid_credentials' }), 'invalid', null],
    [reply(429, { detail: 'too_many_attempts' }, { 'Retry-After': '900' }), 'throttled', 900],
    [reply(503), 'failed', null],
  ])('maps login failures to kinds', async (response, kind, retry) => {
    mockFetch(response)
    const error = await login('a@b.c', 'x').catch((e) => e)
    expect(error).toBeInstanceOf(LoginError)
    expect(error.kind).toBe(kind)
    expect(error.retryAfterSeconds).toBe(retry)
  })

  it('logs out by revoking the refresh session', async () => {
    const fetchMock = mockFetch(reply(204))
    await logout()
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/refresh', expect.objectContaining({ method: 'DELETE' }))
  })

  it.each([
    [reply(400, { detail: 'invite_invalid' }), 'invalid'],
    [reply(422, { detail: 'password_too_short' }), 'too_short'],
    [reply(500), 'failed'],
  ])('maps invite failures to kinds', async (response, kind) => {
    mockFetch(response)
    const error = await acceptInvite('token', 'senha-da-banca-2026').catch((e) => e)
    expect(error).toBeInstanceOf(InviteError)
    expect(error.kind).toBe(kind)
  })

  it('accepts a valid invite', async () => {
    mockFetch(reply(204))
    await expect(acceptInvite('token', 'senha-da-banca-2026')).resolves.toBeUndefined()
  })
})
