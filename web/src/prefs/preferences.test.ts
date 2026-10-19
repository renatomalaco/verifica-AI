import { beforeEach, describe, expect, it } from 'vitest'
import {
  applyPreferences,
  buildConfigLink,
  DEFAULT_PREFERENCES,
  loadPreferences,
  parseConfigHash,
  preferencesFromSituations,
  sanitizePreferences,
  savePreferences,
} from './preferences'

describe('preferences', () => {
  beforeEach(() => {
    localStorage.clear()
    for (const a of ['data-text-size', 'data-contrast', 'data-targets', 'data-motion']) {
      document.documentElement.removeAttribute(a)
    }
  })

  it('starts with every accessibility option turned off', () => {
    expect(loadPreferences()).toEqual(DEFAULT_PREFERENCES)
  })

  it('maps catalog situations to the matching adjustments', () => {
    const prefs = preferencesFromSituations(['tremor', 'visao', 'leitura'])
    expect(prefs.largeTargets).toBe(true)
    expect(prefs.textSize).toBe('large')
    expect(prefs.highContrast).toBe(true)
    expect(prefs.autoSpeak).toBe(true)
    expect(prefs.simpleMode).toBe(false)
  })

  it('ignores unknown keys and invalid values from untrusted input', () => {
    const prefs = sanitizePreferences({ textSize: 'gigante', highContrast: 'sim', motion: 'reduced', evil: '<script>' })
    expect(prefs).toEqual({ ...DEFAULT_PREFERENCES, motion: 'reduced' })
  })

  it('round-trips preferences through the configuration link', () => {
    const prefs = { ...DEFAULT_PREFERENCES, textSize: 'xlarge' as const, simpleMode: true }
    const link = buildConfigLink(prefs, 'https://verifica.example')
    expect(link.startsWith('https://verifica.example/#ajustes=')).toBe(true)
    expect(parseConfigHash(new URL(link).hash)).toEqual(prefs)
  })

  it('returns null for a broken configuration link', () => {
    expect(parseConfigHash('#ajustes=%%%')).toBeNull()
    expect(parseConfigHash('#outra-coisa')).toBeNull()
  })

  it('persists and reloads preferences', () => {
    savePreferences({ ...DEFAULT_PREFERENCES, largeTargets: true })
    expect(loadPreferences().largeTargets).toBe(true)
  })

  it('applies preferences as data attributes and removes them when off', () => {
    const root = document.documentElement
    applyPreferences({ ...DEFAULT_PREFERENCES, textSize: 'large', highContrast: true, largeTargets: true, motion: 'system' })
    expect(root.getAttribute('data-text-size')).toBe('large')
    expect(root.getAttribute('data-contrast')).toBe('high')
    expect(root.getAttribute('data-targets')).toBe('large')
    expect(root.getAttribute('data-motion')).toBe('system')

    applyPreferences(DEFAULT_PREFERENCES)
    expect(root.hasAttribute('data-text-size')).toBe(false)
    expect(root.hasAttribute('data-contrast')).toBe(false)
    expect(root.hasAttribute('data-motion')).toBe(false)
  })
})
