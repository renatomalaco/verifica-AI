// Rules of the research area sign-in (R5a). No React, testable in isolation.
import type { ResearchRole } from '../types'

// Same minimum as scan_orchestrator.domain.research_access; the backend has the final word.
export const MIN_PASSWORD_LENGTH = 12
const DEFAULT_RETRY_SECONDS = 900

export type PasswordProblem = 'too_short' | 'mismatch'

export function canRunStudy(role: ResearchRole): boolean {
  return role === 'admin'
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
