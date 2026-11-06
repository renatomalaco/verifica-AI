import { pickVoice } from '../domain/voice'

// Chrome fills the voice list asynchronously; past this wait, the browser default voice reads.
export const VOICES_TIMEOUT_MS = 1500
const DEFAULT_LANG = 'pt-BR'

// Bumped by every speak or stop, so a speech still waiting for voices knows it was superseded.
let generation = 0

export function isSpeechSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}

export function stopSpeaking(): void {
  generation += 1
  if (isSpeechSupported()) {
    window.speechSynthesis.cancel()
  }
}

function deviceVoices(): Promise<SpeechSynthesisVoice[]> {
  const synth = window.speechSynthesis
  const voices = synth.getVoices()
  if (voices.length > 0 || typeof synth.addEventListener !== 'function') return Promise.resolve(voices)
  return new Promise((resolve) => {
    const done = () => {
      clearTimeout(timer)
      synth.removeEventListener('voiceschanged', done)
      resolve(synth.getVoices())
    }
    const timer = setTimeout(done, VOICES_TIMEOUT_MS)
    synth.addEventListener('voiceschanged', done)
  })
}

export async function speakVerdict(
  text: string,
  onStart?: () => void,
  onEnd?: () => void,
  onError?: () => void
): Promise<void> {
  if (!isSpeechSupported() || !text.trim()) {
    return
  }

  stopSpeaking()
  const mine = generation
  const voice = pickVoice(await deviceVoices())
  if (mine !== generation) return

  const utterance = new SpeechSynthesisUtterance(text)
  utterance.voice = voice
  utterance.lang = voice?.lang.replace('_', '-') ?? DEFAULT_LANG
  utterance.rate = 0.95 // Slightly calmer, clearer pacing for seniors
  utterance.pitch = 1.0

  if (onStart) utterance.onstart = onStart
  if (onEnd) utterance.onend = onEnd
  if (onError) utterance.onerror = onError

  window.speechSynthesis.speak(utterance)
}
