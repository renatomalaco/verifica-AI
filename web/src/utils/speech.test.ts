import { describe, it, expect, vi, beforeEach } from 'vitest'
import { speakVerdict, stopSpeaking, isSpeechSupported } from './speech'

describe('Speech Utility (TTS)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('detects speech synthesis support', () => {
    expect(isSpeechSupported()).toBe(true)
  })

  it('cancels previous speech before speaking new text', () => {
    const cancelSpy = vi.spyOn(window.speechSynthesis, 'cancel')
    const speakSpy = vi.spyOn(window.speechSynthesis, 'speak')

    speakVerdict('Atenção, esta mensagem é um golpe.')

    expect(cancelSpy).toHaveBeenCalledTimes(1)
    expect(speakSpy).toHaveBeenCalledTimes(1)
  })

  it('stops speaking when stopSpeaking is called', () => {
    const cancelSpy = vi.spyOn(window.speechSynthesis, 'cancel')
    stopSpeaking()
    expect(cancelSpy).toHaveBeenCalled()
  })

  it('handles empty text gracefully without throwing', () => {
    const speakSpy = vi.spyOn(window.speechSynthesis, 'speak')
    speakVerdict('')
    expect(speakSpy).not.toHaveBeenCalled()
  })
})
