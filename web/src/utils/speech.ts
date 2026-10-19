export function isSpeechSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}

export function stopSpeaking(): void {
  if (isSpeechSupported()) {
    window.speechSynthesis.cancel()
  }
}

export function speakVerdict(
  text: string,
  onStart?: () => void,
  onEnd?: () => void,
  onError?: () => void
): void {
  if (!isSpeechSupported() || !text.trim()) {
    return
  }

  // Stop any active utterance first
  window.speechSynthesis.cancel()

  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'pt-BR'
  utterance.rate = 0.95 // Slightly calmer, clearer pacing for seniors
  utterance.pitch = 1.0

  if (onStart) utterance.onstart = onStart
  if (onEnd) utterance.onend = onEnd
  if (onError) utterance.onerror = onError

  window.speechSynthesis.speak(utterance)
}
