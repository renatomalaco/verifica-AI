import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { VOICES_TIMEOUT_MS, isSpeechSupported, speakVerdict, stopSpeaking } from './speech'

type FakeVoice = { name: string; lang: string }

// A speechSynthesis whose voice list can arrive late, as in Chrome.
class FakeSynth extends EventTarget {
  voices: FakeVoice[] = []
  spoken: SpeechSynthesisUtterance[] = []
  getVoices = () => this.voices
  speak = vi.fn((utterance: SpeechSynthesisUtterance) => this.spoken.push(utterance))
  cancel = vi.fn()

  loadVoices(voices: FakeVoice[]) {
    this.voices = voices
    this.dispatchEvent(new Event('voiceschanged'))
  }
}

const NATURAL = { name: 'Microsoft Francisca Online (Natural) - Portuguese (Brazil)', lang: 'pt-BR' }
const ROBOTIC = { name: 'Microsoft Maria - Portuguese (Brazil)', lang: 'pt-BR' }

describe('speech', () => {
  let synth: FakeSynth
  const original = window.speechSynthesis

  beforeEach(() => {
    synth = new FakeSynth()
    Object.defineProperty(window, 'speechSynthesis', { value: synth, writable: true, configurable: true })
  })

  afterEach(() => {
    Object.defineProperty(window, 'speechSynthesis', { value: original, writable: true, configurable: true })
    vi.useRealTimers()
  })

  it('detects speech synthesis support', () => {
    expect(isSpeechSupported()).toBe(true)
  })

  it('reads with the most natural Brazilian voice of the device', async () => {
    synth.voices = [ROBOTIC, NATURAL]

    await speakVerdict('Isto é um golpe.')

    expect(synth.spoken[0].voice).toBe(NATURAL)
    expect(synth.spoken[0].lang).toBe('pt-BR')
    expect(synth.spoken[0].text).toBe('Isto é um golpe.')
  })

  it('waits for a voice list that arrives late', async () => {
    const speaking = speakVerdict('Isto é um golpe.')
    expect(synth.speak).not.toHaveBeenCalled()

    synth.loadVoices([ROBOTIC, NATURAL])
    await speaking

    expect(synth.spoken[0].voice).toBe(NATURAL)
  })

  it('speaks with the browser default when no voice list ever arrives', async () => {
    vi.useFakeTimers()
    const speaking = speakVerdict('Isto é um golpe.')

    await vi.advanceTimersByTimeAsync(VOICES_TIMEOUT_MS)
    await speaking

    expect(synth.spoken[0].voice).toBeNull()
    expect(synth.spoken[0].lang).toBe('pt-BR')
  })

  it('does not start speaking if stopped while the voices were loading', async () => {
    const speaking = speakVerdict('Isto é um golpe.')

    stopSpeaking()
    synth.loadVoices([NATURAL])
    await speaking

    expect(synth.speak).not.toHaveBeenCalled()
  })

  it('cancels previous speech before speaking new text', async () => {
    synth.voices = [NATURAL]

    await speakVerdict('Atenção, esta mensagem é um golpe.')

    expect(synth.cancel).toHaveBeenCalledTimes(1)
    expect(synth.speak).toHaveBeenCalledTimes(1)
  })

  it('handles empty text without speaking', async () => {
    await speakVerdict('   ')
    expect(synth.speak).not.toHaveBeenCalled()
  })
})
