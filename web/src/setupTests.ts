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
  })
}

if (!('SpeechSynthesisUtterance' in window)) {
  Object.defineProperty(window, 'SpeechSynthesisUtterance', {
    value: class {
      text: string
      lang: string = 'pt-BR'
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
