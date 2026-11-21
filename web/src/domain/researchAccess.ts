// Rules of the research area sign-in (R5a). No React, testable in isolation.
import { RESEARCH_PERMISSIONS, type ResearchAccount, type ResearchPermission, type ResearchRole } from '../types'

// Same minimum as scan_orchestrator.domain.research_access; the backend has the final word.
export const MIN_PASSWORD_LENGTH = 12
const DEFAULT_RETRY_SECONDS = 900

export type PasswordProblem = 'too_short' | 'mismatch'
export type ResearchSection = 'report' | 'accounts' | 'account'

export const ACCOUNTS_PATH = '/pesquisa/contas'
export const REPORT_PATH = '/pesquisa'

// Id of the role that always keeps access management (contracts.ResearchRole.ADMIN).
const ADMIN_ROLE_ID = 'admin'

export function canViewStudy(role: ResearchRole): boolean {
  return role.permissions.includes('view_study')
}

export function explainsWithoutLimit(role: ResearchRole): boolean {
  return role.permissions.includes('unlimited_explain')
}

export function canRunStudy(role: ResearchRole): boolean {
  return role.permissions.includes('run_study')
}

export function canManageAccounts(role: ResearchRole): boolean {
  return role.permissions.includes('manage_access')
}

// Same rule as check_role_change in the backend: otherwise no one could fix access again.
export function isLockedPermission(roleId: string, permission: ResearchPermission): boolean {
  return roleId === ADMIN_ROLE_ID && permission === 'manage_access'
}

// A researcher who opens the accounts address just sees the report; a family account,
// with neither the study nor accounts, gets a page about what its account allows.
export function researchSection(pathname: string, role: ResearchRole): ResearchSection {
  const wantsAccounts = pathname.startsWith(ACCOUNTS_PATH) || !canViewStudy(role)
  if (wantsAccounts && canManageAccounts(role)) return 'accounts'
  return canViewStudy(role) ? 'report' : 'account'
}

export function togglePermission(permissions: ResearchPermission[], permission: ResearchPermission): ResearchPermission[] {
  const next = permissions.includes(permission) ? permissions.filter((p) => p !== permission) : [...permissions, permission]
  return RESEARCH_PERMISSIONS.filter((p) => next.includes(p))
}

// Blocked accounts no longer use their role, so they are not counted.
export function peoplePerRole(accounts: ResearchAccount[]): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const account of accounts.filter((a) => a.status !== 'disabled')) {
    counts[account.role.id] = (counts[account.role.id] ?? 0) + 1
  }
  return counts
}

// The backend refuses self-blocking too; hiding the button just avoids a dead end.
export function canBlock(account: ResearchAccount, currentEmail: string): boolean {
  return account.status !== 'disabled' && account.email !== currentEmail
}

export function passwordProblem(password: string, confirmation: string): PasswordProblem | null {
  if (password.length < MIN_PASSWORD_LENGTH) return 'too_short'
  if (password !== confirmation) return 'mismatch'
  return null
}

// The invite link carries the token after "#", so it never reaches server logs.
export function inviteTokenFromHash(hash: string): string | null {
  return new URLSearchParams(hash.replace(/^#/, '')).get('token') || null
}

export function retryMinutes(retryAfterSeconds: number | null): number {
  return Math.ceil((retryAfterSeconds ?? DEFAULT_RETRY_SECONDS) / 60)
}

// The server keeps the instant access ends (midnight); people read the last day they can still enter.
export function lastAccessDay(expiresAt: string): Date {
  return new Date(new Date(expiresAt).getTime() - 1)
}
