// Onboarding tutorial steps: shown by Tutorial.tsx and read aloud by its "Ouvir" button.
import { m } from '../paraglide/messages.js'

export interface TutorialStep {
  title: () => string
  text: () => string
}

export const TUTORIAL_STEPS: TutorialStep[] = [
  { title: m.onboarding_tutorial_step_1_title, text: m.onboarding_tutorial_step_1_text },
  { title: m.onboarding_tutorial_step_2_title, text: m.onboarding_tutorial_step_2_text },
  { title: m.onboarding_tutorial_step_3_title, text: m.onboarding_tutorial_step_3_text },
]

export const tutorialSpeechText = (step: TutorialStep): string => `${step.title()}. ${step.text()}`
