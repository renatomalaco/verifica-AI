import { describe, expect, it } from 'vitest'
import { spokenVerdictText } from '../domain/verdict'
import { VERDICT_MESSAGES } from '../types'
import { lessons, lessonSpeechText } from './lessons'
import { spokenTexts } from './spoken'
import { TUTORIAL_STEPS, tutorialSpeechText } from './tutorial'

describe('spokenTexts', () => {
  const texts = spokenTexts()

  it('covers every verdict the backend can send, whatever the threat level', () => {
    for (const verdict_message of VERDICT_MESSAGES) {
      expect(texts).toContain(spokenVerdictText({ threat_level: 'GOLPE', verdict_message }))
      expect(texts).toContain(spokenVerdictText({ threat_level: 'SEGURO', verdict_message }))
    }
  })

  it('covers every lesson', () => {
    for (const lesson of lessons()) expect(texts).toContain(lessonSpeechText(lesson))
  })

  it('covers every tutorial step', () => {
    for (const step of TUTORIAL_STEPS) expect(texts).toContain(tutorialSpeechText(step))
  })
})
