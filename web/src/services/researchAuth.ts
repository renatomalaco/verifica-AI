// Research area sign-in (R5a). Tokens live in httpOnly cookies: this code never sees them.
import type { ResearchUser } from '../types'

const AUTH = '/api/v1/auth'

export class SignedOutError extends Error {
  constructor() {
    super('signed_out')
    this.name = 'SignedOutError'
  }
}

export type LoginErrorKind = 'invalid' | 'throttled' | 'failed'

export class LoginError extends Error {
  kind: LoginErrorKind
  retryAfterSeconds: number | null

  constructor(kind: LoginErrorKind, retryAfterSeconds: number | null = null) {
    super(kind)
    this.name = 'LoginError'
    this.kind = kind
    this.retryAfterSeconds = retryAfterSeconds
  }
}

export type InviteErrorKind = 'invalid' | 'too_short' | 'failed'

export class InviteError extends Error {
  kind: InviteErrorKind

  constructor(kind: InviteErrorKind) {
    super(kind)
    this.name = 'InviteError'
    this.kind = kind
  }
}

const postJson = (body: unknown): RequestInit => ({
  method: 'POST',
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

let renewing: Promise<boolean> | null = null

// Single flight: a second rotation with the same refresh token would look like theft and end the session.
function renewSession(): Promise<boolean> {
  renewing ??= fetch(`${AUTH}/refresh`, { method: 'POST', credentials: 'same-origin' })
    .then((response) => response.ok)
    .catch(() => false)
    .finally(() => {
      renewing = null
    })
  return renewing
}

// Fetch for protected routes: renews the 15-minute access once when it expires.
export async function researchFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const request = () => fetch(path, { credentials: 'same-origin', ...init })
  const response = await request()
  if (response.status !== 401) return response
  if (!(await renewSession())) throw new SignedOutError()
  const retried = await request()
  if (retried.status === 401) throw new SignedOutError()
  return retried
}

export async function fetchCurrentUser(): Promise<ResearchUser | null> {
  try {
    const response = await researchFetch(`${AUTH}/me`)
    if (!response.ok) throw new Error(`Session check failed (${response.status})`)
    return await response.json()
  } catch (err) {
    if (err instanceof SignedOutError) return null
    throw err
  }
}

function retryAfter(response: Response): number | null {
  const seconds = Number(response.headers.get('Retry-After'))
  return Number.isFinite(seconds) && seconds > 0 ? seconds : null
}

export async function login(email: string, password: string): Promise<ResearchUser> {
  const response = await fetch(`${AUTH}/login`, postJson({ email, password })).catch(() => null)
  if (response?.status === 401) throw new LoginError('invalid')
  if (response?.status === 429) throw new LoginError('throttled', retryAfter(response))
  if (!response?.ok) throw new LoginError('failed')
  return response.json()
}

export async function logout(): Promise<void> {
  // Even if this call fails, the screen signs out; the access cookie dies in at most 15 minutes.
  await fetch(`${AUTH}/refresh`, { method: 'DELETE', credentials: 'same-origin' }).catch(() => null)
}

const INVITE_ERRORS: Record<string, InviteErrorKind> = {
  invite_invalid: 'invalid',
  password_too_short: 'too_short',
}

export async function acceptInvite(token: string, password: string): Promise<void> {
  const response = await fetch(`${AUTH}/invites/accept`, postJson({ token, password })).catch(() => null)
  if (response?.ok) return
  const body = await response?.json().catch(() => ({}))
  throw new InviteError(INVITE_ERRORS[body?.detail] ?? 'failed')
}
