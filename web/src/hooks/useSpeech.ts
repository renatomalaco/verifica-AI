import { useEffect, useRef, useState } from 'react'
import { isSpeechSupported, speakVerdict, stopSpeaking } from '../utils/speech'

interface SpeechOptions {
  // Auto-speak preference: starts speaking as soon as the screen opens.
  startOnMount?: boolean
}

export function useSpeech(text: string, { startOnMount = false }: SpeechOptions = {}) {
  const [speaking, setSpeaking] = useState(() => startOnMount && isSpeechSupported())
  const initial = useRef({ speaking, text })

  useEffect(() => {
    const { speaking: autoStart, text: firstText } = initial.current
    if (autoStart) speakVerdict(firstText, undefined, () => setSpeaking(false), () => setSpeaking(false))
    return () => stopSpeaking()
  }, [])

  const toggle = () => {
    stopSpeaking()
    if (speaking) {
      setSpeaking(false)
      return
    }
    setSpeaking(true)
    speakVerdict(text, undefined, () => setSpeaking(false), () => setSpeaking(false))
  }

  return { speaking, toggle }
}
