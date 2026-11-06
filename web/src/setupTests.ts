import '@testing-library/jest-dom'

// Mock SpeechSynthesis if not available in jsdom
if (!('speechSynthesis' in window)) {
  Object.defineProperty(window, 'speechSynthesis', {
    value: {
      speak: () => {},
      cancel: () => {},
      pause: () => {},
      resume: () => {},
      getVoices: () => [],
      speaking: false,
      paused: false,
      pending: false,
    },
    writable: true,
    configurable: true,
  })
}

if (!('SpeechSynthesisUtterance' in window)) {
  Object.defineProperty(window, 'SpeechSynthesisUtterance', {
    value: class {
      text: string
      lang: string = ''
      voice: SpeechSynthesisVoice | null = null
      rate = 1
      pitch = 1
      onend: (() => void) | null = null
      onerror: (() => void) | null = null
      constructor(text: string) {
        this.text = text
      }
    },
    writable: true,
  })
}

// jsdom doesn't implement scrolling.
window.scrollTo = () => {}
