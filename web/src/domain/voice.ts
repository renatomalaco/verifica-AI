// Which device voice reads the verdict aloud. No React and no browser API, testable in isolation.

export interface VoiceInfo {
  name: string
  lang: string
}

// Neural voices sound human; the browser default is often the most robotic one (on Windows).
const NATURAL = /natural|online|neural|google|premium|enhanced/i

// Brazilian Portuguese first, then any Portuguese: still better than an English voice reading Portuguese.
function languageRank(lang: string): number {
  const tag = lang.replace('_', '-').toLowerCase()
  if (tag === 'pt-br') return 2
  if (tag.startsWith('pt')) return 1
  return 0
}

const score = (voice: VoiceInfo) => languageRank(voice.lang) * 2 + (NATURAL.test(voice.name) ? 1 : 0)

/** The best Portuguese voice on the device, or null to let the browser choose by language. */
export function pickVoice<T extends VoiceInfo>(voices: readonly T[]): T | null {
  const candidates = voices.filter((voice) => languageRank(voice.lang) > 0)
  if (candidates.length === 0) return null
  return candidates.reduce((best, voice) => (score(voice) > score(best) ? voice : best))
}
