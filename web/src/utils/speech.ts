import recordings from '../content/recordings.json'
import { pickVoice, recordingFile } from '../domain/voice'
import { getLocale } from '../paraglide/runtime.js'

// Chrome fills the voice list asynchronously; past this wait, the browser default voice reads.
export const VOICES_TIMEOUT_MS = 1500
const DEFAULT_LANG = 'pt-BR'

// Fixed texts recorded once by scripts/render-voice.mjs: the same calm voice on every device.
const RECORDED: ReadonlySet<string> = new Set(recordings.keys)

// Bumped by every speak or stop, so a speech still waiting for voices knows it was superseded.
let generation = 0
let playing: HTMLAudioElement | null = null

export function isSpeechSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}

export function stopSpeaking(): void {
  generation += 1
  playing?.pause()
  playing = null
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

interface SpeechEvents {
  onStart?: () => void
  onEnd?: () => void
  onError?: () => void
}

export async function speakVerdict(
  text: string,
  onStart?: () => void,
  onEnd?: () => void,
  onError?: () => void
): Promise<void> {
  if (!text.trim()) return

  stopSpeaking()
  const events = { onStart, onEnd, onError }
  const file = recordingFile(RECORDED, getLocale(), text)
  if (file) return playRecording(import.meta.env.BASE_URL + file, text, events)
  return speakWithDeviceVoice(text, events)
}

// A missing file, no network or a blocked autoplay: the device voice reads instead.
function playRecording(url: string, text: string, events: SpeechEvents): Promise<void> {
  const mine = generation
  const fallBack = () => {
    if (mine !== generation) return
    stopSpeaking()
    return speakWithDeviceVoice(text, events)
  }

  const audio = new Audio(url)
  playing = audio
  if (events.onStart) audio.onplaying = events.onStart
  if (events.onEnd) audio.onended = events.onEnd
  audio.onerror = fallBack
  return audio.play().catch(fallBack)
}

async function speakWithDeviceVoice(text: string, { onStart, onEnd, onError }: SpeechEvents): Promise<void> {
  if (!isSpeechSupported()) return

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
