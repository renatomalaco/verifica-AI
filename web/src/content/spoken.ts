// Every fixed text the app reads aloud. scripts/render-voice.mjs records each one; a text
// missing here still works, read by a device voice.
import { allSpokenVerdicts } from '../domain/verdict'
import { lessons, lessonSpeechText } from './lessons'
import { TUTORIAL_STEPS, tutorialSpeechText } from './tutorial'

export const spokenTexts = (): string[] => [
  ...allSpokenVerdicts(),
  ...lessons().map(lessonSpeechText),
  ...TUTORIAL_STEPS.map(tutorialSpeechText),
]
