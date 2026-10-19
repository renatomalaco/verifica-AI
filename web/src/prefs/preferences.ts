// Accessibility preferences: all optional and off by default
// (decision recorded in PRODUCT.md › Accessibility & Inclusion).
// Stored only on this device and carried in the setup link,
// which holds only these options and never personal data.
import { m } from '../paraglide/messages.js'

export type TextSize = 'normal' | 'large' | 'xlarge'
export type Motion = 'full' | 'reduced' | 'system'

export interface Preferences {
  textSize: TextSize
  highContrast: boolean
  largeTargets: boolean
  motion: Motion
  screenReader: boolean
  simpleMode: boolean
  autoSpeak: boolean
}

export const DEFAULT_PREFERENCES: Preferences = {
  textSize: 'normal',
  highContrast: false,
  largeTargets: false,
  motion: 'full',
  screenReader: false,
  simpleMode: false,
  autoSpeak: false,
}

export interface Situation {
  id: string
  title: () => string
  description: () => string
  apply: Partial<Preferences>
}

// Catalog explained by the user's situation, not by the setting's technical name.
export const SITUATIONS: Situation[] = [
  {
    id: 'tremor',
    title: m.settings_situation_tremor_title,
    description: m.settings_situation_tremor_description,
    apply: { largeTargets: true },
  },
  {
    id: 'visao',
    title: m.settings_situation_vision_title,
    description: m.settings_situation_vision_description,
    apply: { textSize: 'large', highContrast: true },
  },
  {
    id: 'leitor',
    title: m.settings_situation_screen_reader_title,
    description: m.settings_situation_screen_reader_description,
    apply: { screenReader: true },
  },
  {
    id: 'memoria',
    title: m.settings_situation_memory_title,
    description: m.settings_situation_memory_description,
    apply: { simpleMode: true },
  },
  {
    id: 'movimento',
    title: m.settings_situation_motion_title,
    description: m.settings_situation_motion_description,
    apply: { motion: 'reduced' },
  },
  {
    id: 'leitura',
    title: m.settings_situation_reading_title,
    description: m.settings_situation_reading_description,
    apply: { autoSpeak: true },
  },
]

const STORAGE_KEY = 'vf.preferences'
const ONBOARDED_KEY = 'vf.onboarded'
export const CONFIG_HASH_PREFIX = '#ajustes='

export function preferencesFromSituations(ids: string[], base: Preferences = DEFAULT_PREFERENCES): Preferences {
  return SITUATIONS.filter((s) => ids.includes(s.id)).reduce<Preferences>(
    (acc, s) => ({ ...acc, ...s.apply }),
    { ...base }
  )
}

// Accept only known keys and values: the link comes from outside and is untrusted.
export function sanitizePreferences(raw: unknown): Preferences {
  const out: Preferences = { ...DEFAULT_PREFERENCES }
  if (!raw || typeof raw !== 'object') return out
  const r = raw as Record<string, unknown>
  if (r.textSize === 'normal' || r.textSize === 'large' || r.textSize === 'xlarge') out.textSize = r.textSize
  if (r.motion === 'full' || r.motion === 'reduced' || r.motion === 'system') out.motion = r.motion
  for (const key of ['highContrast', 'largeTargets', 'screenReader', 'simpleMode', 'autoSpeak'] as const) {
    if (typeof r[key] === 'boolean') out[key] = r[key] as boolean
  }
  return out
}

export function loadPreferences(): Preferences {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    return stored ? sanitizePreferences(JSON.parse(stored)) : { ...DEFAULT_PREFERENCES }
  } catch {
    return { ...DEFAULT_PREFERENCES }
  }
}

export function savePreferences(prefs: Preferences): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
  } catch {
    // No storage (private mode): applies only to this visit.
  }
}

export function applyPreferences(prefs: Preferences, root: HTMLElement = document.documentElement): void {
  const set = (name: string, value: string | null) => {
    if (value === null) root.removeAttribute(name)
    else root.setAttribute(name, value)
  }
  set('data-text-size', prefs.textSize === 'normal' ? null : prefs.textSize)
  set('data-contrast', prefs.highContrast ? 'high' : null)
  set('data-targets', prefs.largeTargets ? 'large' : null)
  set('data-motion', prefs.motion === 'full' ? null : prefs.motion)
}

export function hasOnboarded(): boolean {
  try {
    return window.localStorage.getItem(ONBOARDED_KEY) === '1'
  } catch {
    return false
  }
}

export function markOnboarded(): void {
  try {
    window.localStorage.setItem(ONBOARDED_KEY, '1')
  } catch {
    // No storage: the tutorial shows again on the next visit.
  }
}

function toBase64Url(text: string): string {
  const bytes = new TextEncoder().encode(text)
  let bin = ''
  bytes.forEach((b) => (bin += String.fromCharCode(b)))
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function fromBase64Url(value: string): string {
  const b64 = value.replace(/-/g, '+').replace(/_/g, '/')
  const bin = atob(b64 + '='.repeat((4 - (b64.length % 4)) % 4))
  return new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0)))
}

export function buildConfigLink(prefs: Preferences, origin: string = window.location.origin): string {
  return `${origin}/${CONFIG_HASH_PREFIX}${toBase64Url(JSON.stringify(prefs))}`
}

export function parseConfigHash(hash: string): Preferences | null {
  if (!hash.startsWith(CONFIG_HASH_PREFIX)) return null
  try {
    return sanitizePreferences(JSON.parse(fromBase64Url(hash.slice(CONFIG_HASH_PREFIX.length))))
  } catch {
    return null
  }
}
