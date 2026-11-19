// Which voice reads a text aloud: a pre-recorded file or a device voice. No React and no browser API.

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

// cyrb53: a tiny 53-bit string hash. Synchronous and the same in the render script (Node) and in
// any browser, unlike crypto.subtle, which only exists on HTTPS pages.
function hash(text: string): number {
  let h1 = 0xdeadbeef
  let h2 = 0x41c6ce57
  for (let i = 0; i < text.length; i++) {
    const ch = text.charCodeAt(i)
    h1 = Math.imul(h1 ^ ch, 2654435761)
    h2 = Math.imul(h2 ^ ch, 1597334677)
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909)
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909)
  return 4294967296 * (2097151 & h2) + (h1 >>> 0)
}

/** Names the pre-recorded audio of a fixed text: any change to the wording asks for a new recording. */
export const recordingKey = (locale: string, text: string): string => hash(`${locale}\n${text}`).toString(16)

/** Path (relative to the site root) of the recording of this text, or null to use a device voice. */
export function recordingFile(recorded: ReadonlySet<string>, locale: string, text: string): string | null {
  const key = recordingKey(locale, text)
  return recorded.has(key) ? `voice/${key}.mp3` : null
}

export interface VoiceModel {
  model: string
  voice: string
}

/** What scripts/render-voice.mjs already recorded (src/content/recordings.json). */
export interface Recordings extends VoiceModel {
  keys: string[]
}

export interface Recording {
  key: string
  locale: string
  text: string
}

/** Which recordings stay and which texts still need one; another model or voice records everything again. */
export function planRecordings(previous: Recordings, next: VoiceModel, wanted: Recording[]) {
  const sameVoice = previous.model === next.model && previous.voice === next.voice
  const recorded = new Set(sameVoice ? previous.keys : [])
  const unique = [...new Map(wanted.map((recording) => [recording.key, recording])).values()]
  return {
    keep: unique.filter(({ key }) => recorded.has(key)).map(({ key }) => key),
    render: unique.filter(({ key }) => !recorded.has(key)),
  }
}
