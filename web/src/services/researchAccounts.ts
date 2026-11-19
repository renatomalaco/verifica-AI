// Admin screen of the research area: accounts, invite links and blocking.
import type { ResearchAccount, ResearchRole } from '../types'
import { postJson, researchFetch } from './researchAuth'

const AUTH = '/api/v1/auth'

export type AccountErrorKind = 'self' | 'not_found' | 'failed'

export class AccountError extends Error {
  kind: AccountErrorKind

  constructor(kind: AccountErrorKind) {
    super(kind)
    this.name = 'AccountError'
    this.kind = kind
  }
}

export interface InviteRequest {
  email: string
  role: ResearchRole
  expiresOn: string // YYYY-MM-DD from the date field; empty means no end
}

const DISABLE_ERRORS: Record<string, AccountErrorKind> = {
  cannot_disable_self: 'self',
  account_not_found: 'not_found',
}

export async function listAccounts(): Promise<ResearchAccount[]> {
  const response = await researchFetch(`${AUTH}/accounts`)
  if (!response.ok) throw new AccountError('failed')
  return response.json()
}

export async function createInvite({ email, role, expiresOn }: InviteRequest): Promise<string> {
  const body = { email, role, expires_on: expiresOn || null }
  const response = await researchFetch(`${AUTH}/invites`, postJson(body))
  if (!response.ok) throw new AccountError('failed')
  return (await response.json()).url
}

export async function disableAccount(email: string): Promise<void> {
  const response = await researchFetch(`${AUTH}/accounts/disable`, postJson({ email }))
  if (response.ok) return
  const body = await response.json().catch(() => ({}))
  throw new AccountError(DISABLE_ERRORS[body?.detail] ?? 'failed')
}
