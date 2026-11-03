import { describe, expect, it } from 'vitest'
import { canRunStudy, inviteTokenFromHash, lastAccessDay, passwordProblem, retryMinutes } from './researchAccess'

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
})

