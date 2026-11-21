import { describe, expect, it } from 'vitest'
import {
  canBlock,
  canManageAccounts,
  canRunStudy,
  isLockedPermission,
  inviteTokenFromHash,
  lastAccessDay,
  passwordProblem,
  researchSection,
  retryMinutes,
} from './researchAccess'
import type { ResearchAccount, ResearchRole } from '../types'

const ADMIN: ResearchRole = { id: 'admin', name: 'Administrador', permissions: ['run_study', 'manage_access'] }
const RESEARCHER: ResearchRole = { id: 'researcher', name: 'Pesquisador', permissions: [] }

describe('research access rules', () => {
  it('lets only the admin run the study', () => {
    expect(canRunStudy(ADMIN)).toBe(true)
    expect(canRunStudy(RESEARCHER)).toBe(false)
    expect(canRunStudy({ id: 'cargo-1', name: 'Orientador', permissions: ['run_study'] })).toBe(true)
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
    expect(canManageAccounts(ADMIN)).toBe(true)
    expect(canManageAccounts(RESEARCHER)).toBe(false)
  })

  it('opens the accounts screen only for the admin', () => {
    expect(researchSection('/pesquisa/contas', ADMIN)).toBe('accounts')
    expect(researchSection('/pesquisa/contas', RESEARCHER)).toBe('report')
    expect(researchSection('/pesquisa', ADMIN)).toBe('report')
  })

  it('offers blocking for other accounts that are not blocked yet', () => {
    const account = (email: string, status: ResearchAccount['status']): ResearchAccount => ({
      email,
      role: RESEARCHER,
      expires_at: null,
      status,
    })
    expect(canBlock(account('banca@exemplo.com', 'active'), 'autor@exemplo.com')).toBe(true)
    expect(canBlock(account('banca@exemplo.com', 'invited'), 'autor@exemplo.com')).toBe(true)
    expect(canBlock(account('banca@exemplo.com', 'disabled'), 'autor@exemplo.com')).toBe(false)
    expect(canBlock(account('autor@exemplo.com', 'active'), 'autor@exemplo.com')).toBe(false)
  })

  it('keeps access management locked on the admin role, like the backend', () => {
    expect(isLockedPermission('admin', 'manage_access')).toBe(true)
    expect(isLockedPermission('admin', 'run_study')).toBe(false)
    expect(isLockedPermission('cargo-1', 'manage_access')).toBe(false)
  })
})
