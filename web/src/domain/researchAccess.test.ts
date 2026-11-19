import { describe, expect, it } from 'vitest'
import {
  canBlock,
  canManageAccounts,
  canRunStudy,
  inviteTokenFromHash,
  lastAccessDay,
  passwordProblem,
  researchSection,
  retryMinutes,
} from './researchAccess'
import type { ResearchAccount } from '../types'

describe('research access rules', () => {
  it('lets only the admin run the study', () => {
    expect(canRunStudy('admin')).toBe(true)
    expect(canRunStudy('researcher')).toBe(false)
  })

  it('asks for at least twelve characters, like the backend', () => {
    expect(passwordProblem('onze-letras', 'onze-letras')).toBe('too_short')
    expect(passwordProblem('doze-letras!', 'doze-letras!')).toBeNull()
  })

  it('catches a mistyped confirmation', () => {
    expect(passwordProblem('doze-letras!', 'doze-letras?')).toBe('mismatch')
  })

  it('reads the invite token from the link fragment', () => {
    expect(inviteTokenFromHash('#token=abc-DEF_123')).toBe('abc-DEF_123')
    expect(inviteTokenFromHash('')).toBeNull()
    expect(inviteTokenFromHash('#outra=coisa')).toBeNull()
  })

  it('rounds the wait up to whole minutes', () => {
    expect(retryMinutes(900)).toBe(15)
    expect(retryMinutes(61)).toBe(2)
    expect(retryMinutes(null)).toBe(15)
  })

  it('shows the last day of access, not the midnight when it ends', () => {
    // The CLI stores "--expires-on 2026-12-20" as midnight of the 21st in Brasília (03:00 UTC).
    const day = lastAccessDay('2026-12-21T03:00:00Z')
    expect(day.toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' })).toBe('20/12/2026')
  })

  it('lets only the admin manage accounts', () => {
    expect(canManageAccounts('admin')).toBe(true)
    expect(canManageAccounts('researcher')).toBe(false)
  })

  it('opens the accounts screen only for the admin', () => {
    expect(researchSection('/pesquisa/contas', 'admin')).toBe('accounts')
    expect(researchSection('/pesquisa/contas', 'researcher')).toBe('report')
    expect(researchSection('/pesquisa', 'admin')).toBe('report')
  })

  it('offers blocking for other accounts that are not blocked yet', () => {
    const account = (email: string, status: ResearchAccount['status']): ResearchAccount => ({
      email,
      role: 'researcher',
      expires_at: null,
      status,
    })
    expect(canBlock(account('banca@exemplo.com', 'active'), 'autor@exemplo.com')).toBe(true)
    expect(canBlock(account('banca@exemplo.com', 'invited'), 'autor@exemplo.com')).toBe(true)
    expect(canBlock(account('banca@exemplo.com', 'disabled'), 'autor@exemplo.com')).toBe(false)
    expect(canBlock(account('autor@exemplo.com', 'active'), 'autor@exemplo.com')).toBe(false)
  })
})
