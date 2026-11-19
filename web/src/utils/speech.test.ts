import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { recordingKey } from '../domain/voice'
import { VOICES_TIMEOUT_MS, isSpeechSupported, speakVerdict, stopSpeaking } from './speech'

// Only this text has a pre-recorded file; every other text goes to the device voice.
vi.mock('../content/recordings.json', async () => {
  const { recordingKey } = await import('../domain/voice')
  return { default: { model: 'gemini-tts', voice: 'Sulafat', keys: [recordingKey('pt-BR', 'Texto gravado.')] } }
})
const RECORDED = 'Texto gravado.'

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

// An HTMLAudioElement whose play() settles when the test decides, like a file still downloading.
class FakeAudio {
  static created: FakeAudio[] = []
  onended: (() => void) | null = null
  onerror: (() => void) | null = null
  paused = true
  pause = vi.fn(() => {
    this.paused = true
  })
  private settle!: { resolve: () => void; reject: (error: Error) => void }
  play = vi.fn(
    () =>
      new Promise<void>((resolve, reject) => {
        this.paused = false
        this.settle = { resolve, reject }
      })
  )

  readonly src: string

  constructor(src: string) {
    this.src = src
    FakeAudio.created.push(this)
  }

  started() {
    this.settle.resolve()
  }

  failed() {
    this.settle.reject(new Error('NotAllowedError'))
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
    FakeAudio.created = []
    vi.stubGlobal('Audio', FakeAudio)
  })

  afterEach(() => {
    Object.defineProperty(window, 'speechSynthesis', { value: original, writable: true, configurable: true })
    vi.useRealTimers()
    vi.unstubAllGlobals()
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

  describe('with a pre-recorded voice', () => {
    beforeEach(() => {
      synth.voices = [NATURAL]
    })

    it('plays the recording of a recorded text instead of the device voice', async () => {
      const speaking = speakVerdict(RECORDED)
      const audio = FakeAudio.created[0]
      audio.started()
      await speaking

      expect(audio.src).toBe(`/voice/${recordingKey('pt-BR', RECORDED)}.mp3`)
      expect(audio.play).toHaveBeenCalledTimes(1)
      expect(synth.speak).not.toHaveBeenCalled()
    })

    it('uses the device voice for a text without a recording', async () => {
      await speakVerdict('Isto é um golpe.')

      expect(FakeAudio.created).toEqual([])
      expect(synth.spoken[0].text).toBe('Isto é um golpe.')
    })

    it('tells when the recording ends', async () => {
      const onEnd = vi.fn()
      const speaking = speakVerdict(RECORDED, undefined, onEnd)
      FakeAudio.created[0].started()
      await speaking

      FakeAudio.created[0].onended?.()

      expect(onEnd).toHaveBeenCalledTimes(1)
    })

    it('falls back to the device voice when the recording cannot play', async () => {
      const speaking = speakVerdict(RECORDED)
      FakeAudio.created[0].failed()
      await speaking
      await vi.waitFor(() => expect(synth.speak).toHaveBeenCalledTimes(1))

      expect(synth.spoken[0].text).toBe(RECORDED)
    })

    it('falls back only once when the file fails to load and play rejects too', async () => {
      const speaking = speakVerdict(RECORDED)
      FakeAudio.created[0].onerror?.()
      FakeAudio.created[0].failed()
      await speaking
      await vi.waitFor(() => expect(synth.speak).toHaveBeenCalled())

      expect(synth.speak).toHaveBeenCalledTimes(1)
    })

    it('stops the recording when speech is stopped', async () => {
      const speaking = speakVerdict(RECORDED)
      FakeAudio.created[0].started()
      await speaking

      stopSpeaking()

      expect(FakeAudio.created[0].pause).toHaveBeenCalled()
    })

    it('does not fall back to the device voice once a stopped recording rejects', async () => {
      const speaking = speakVerdict(RECORDED)
      stopSpeaking()
      FakeAudio.created[0].failed()
      await speaking

      expect(synth.speak).not.toHaveBeenCalled()
    })

    it('stops the previous recording when a new text starts', async () => {
      const first = speakVerdict(RECORDED)
      FakeAudio.created[0].started()
      await first

      await speakVerdict('Isto é um golpe.')

      expect(FakeAudio.created[0].pause).toHaveBeenCalled()
      expect(synth.spoken[0].text).toBe('Isto é um golpe.')
    })
  })
})
