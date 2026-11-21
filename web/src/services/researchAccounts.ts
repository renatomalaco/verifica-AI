// Admin screen of the research area: accounts, invite links, blocking and roles.
import type { ResearchAccount, ResearchPermission, ResearchRole } from '../types'
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
  role: string // ResearchRole.id
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

export type RoleErrorKind = 'name_taken' | 'protected' | 'not_found' | 'failed'

export class RoleError extends Error {
  kind: RoleErrorKind

  constructor(kind: RoleErrorKind) {
    super(kind)
    this.name = 'RoleError'
    this.kind = kind
  }
}

export interface RoleDraft {
  name: string
  permissions: ResearchPermission[]
}

const ROLE_ERRORS: Record<string, RoleErrorKind> = {
  role_name_taken: 'name_taken',
  protected_role: 'protected',
  role_not_found: 'not_found',
}

export async function listRoles(): Promise<ResearchRole[]> {
  const response = await researchFetch(`${AUTH}/roles`)
  if (!response.ok) throw new RoleError('failed')
  return response.json()
}

export const createRole = (draft: RoleDraft): Promise<ResearchRole> =>
  saveRole(`${AUTH}/roles`, postJson(draft))

export const updateRole = (id: string, draft: RoleDraft): Promise<ResearchRole> =>
  saveRole(`${AUTH}/roles/${encodeURIComponent(id)}`, { ...postJson(draft), method: 'PUT' })

async function saveRole(path: string, init: RequestInit): Promise<ResearchRole> {
  const response = await researchFetch(path, init)
  if (response.ok) return response.json()
  const body = await response.json().catch(() => ({}))
  throw new RoleError(ROLE_ERRORS[body?.detail] ?? 'failed')
}
