import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Learn } from './Learn'
import { lessons, lessonForCategory, lessonSpeechText, loadLessonProgress } from '../content/lessons'
import { m } from '../paraglide/messages.js'

describe('Learn', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('lists the golden rules and every lesson with progress', () => {
    render(<Learn onBack={() => {}} />)
    expect(screen.getByRole('heading', { level: 1, name: m.learn_title() })).toHaveFocus()
    expect(screen.getByRole('heading', { name: m.learn_golden_rules_title() })).toBeInTheDocument()
    expect(screen.getByText(m.learn_progress({ done: 0, total: lessons().length }))).toBeInTheDocument()
    for (const lesson of lessons()) {
      expect(screen.getByRole('button', { name: new RegExp(lesson.title) })).toBeInTheDocument()
    }
  })

  it('opens a lesson, gives feedback on the exercise and saves progress', () => {
    render(<Learn onBack={() => {}} />)
    const [first, second] = lessons()
    fireEvent.click(screen.getByRole('button', { name: new RegExp(first.title) }))

    expect(screen.getByRole('heading', { level: 1, name: first.title })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: m.learn_signs_title() })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: m.learn_quiz_scam() }))
    expect(screen.getByRole('status')).toHaveTextContent(`${m.learn_feedback_correct()} ${m.learn_feedback_scam()}`)
    expect(loadLessonProgress()).toEqual(['falso-parente'])

    fireEvent.click(screen.getByRole('button', { name: m.learn_next_lesson() }))
    expect(screen.getByRole('heading', { level: 1, name: second.title })).toBeInTheDocument()
  })

  it('explains gently when the answer is wrong', () => {
    render(<Learn onBack={() => {}} initialLessonId="mensagens-normais" />)
    fireEvent.click(screen.getByRole('button', { name: m.learn_quiz_scam() }))
    expect(screen.getByRole('status')).toHaveTextContent(`${m.learn_feedback_wrong()} ${m.learn_feedback_not_scam()}`)
  })

  it('goes back from the lesson list', () => {
    const onBack = vi.fn()
    render(<Learn onBack={onBack} />)
    fireEvent.click(screen.getByRole('button', { name: m.common_back() }))
    expect(onBack).toHaveBeenCalledTimes(1)
  })
})

describe('lessonForCategory', () => {
  it('maps verdict categories to the lesson that explains them', () => {
    expect(lessonForCategory('coercao_afetiva')).toBe('falso-parente')
    expect(lessonForCategory('brand_spoofing')).toBe('links-falsos')
    expect(lessonForCategory('desconhecida')).toBeNull()
    expect(lessonForCategory(null)).toBeNull()
  })
})

describe('lessonSpeechText', () => {
  it('reads the lesson in order: title, how it works, signs and what to do', () => {
    const [lesson] = lessons()
    const text = lessonSpeechText(lesson)
    expect(text.startsWith(lesson.title)).toBe(true)
    expect(text.indexOf(m.learn_speech_signs())).toBeLessThan(text.indexOf(m.learn_speech_do_this()))
    expect(text).toContain(lesson.doThis[0])
  })
})
