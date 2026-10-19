// Course "Learn to protect yourself": locale-agnostic rules. The text lives
// in one content module per locale because it is long, structured prose.
import { m } from '../paraglide/messages.js'
import { getLocale } from '../paraglide/runtime.js'
import * as ptBR from './pt-BR/lessons'

export interface Lesson {
  id: string
  title: string
  summary: string
  howItWorks: string
  signs: string[]
  doThis: string[]
  quiz: {
    message: string
    isScam: boolean
    explanation: string
  }
}

const CONTENT: Record<ReturnType<typeof getLocale>, { GOLDEN_RULES: string[]; LESSONS: Lesson[] }> = {
  'pt-BR': ptBR,
}

// Functions, not constants, so the content follows the locale at call time.
export const goldenRules = (): string[] => CONTENT[getLocale()].GOLDEN_RULES
export const lessons = (): Lesson[] => CONTENT[getLocale()].LESSONS

export function lessonSpeechText(lesson: Lesson): string {
  return [
    lesson.title,
    lesson.howItWorks,
    m.learn_speech_signs(),
    ...lesson.signs,
    m.learn_speech_do_this(),
    ...lesson.doThis,
  ].join(' ')
}

// Maps the verdict category to the lesson explaining that kind of scam.
const LESSON_BY_CATEGORY: Record<string, string> = {
  coercao_afetiva: 'falso-parente',
  urgencia: 'falso-parente',
  ameaca_financeira: 'central-banco',
  brand_spoofing: 'links-falsos',
  blacklist_feed: 'links-falsos',
  embedded_phishing_link: 'links-falsos',
  antibot_challenge: 'links-falsos',
}

export function lessonForCategory(category: string | null | undefined): string | null {
  return (category && LESSON_BY_CATEGORY[category]) || null
}

const PROGRESS_KEY = 'vf.lessons'

export function loadLessonProgress(): string[] {
  try {
    const raw = JSON.parse(window.localStorage.getItem(PROGRESS_KEY) ?? '[]')
    return Array.isArray(raw) ? raw.filter((id) => lessons().some((l) => l.id === id)) : []
  } catch {
    return []
  }
}

export function saveLessonProgress(ids: string[]): void {
  try {
    window.localStorage.setItem(PROGRESS_KEY, JSON.stringify(ids))
  } catch {
    // No storage: progress lasts only for this visit.
  }
}
