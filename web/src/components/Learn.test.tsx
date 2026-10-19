import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Learn } from './Learn'
import { LESSONS, lessonForCategory, lessonSpeechText, loadLessonProgress } from '../content/lessons'

describe('Learn', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('lists the golden rules and every lesson with progress', () => {
    render(<Learn onBack={() => {}} />)
    expect(screen.getByRole('heading', { level: 1, name: 'Aprenda a se proteger' })).toHaveFocus()
    expect(screen.getByRole('heading', { name: 'As 5 regras de ouro' })).toBeInTheDocument()
    expect(screen.getByText(`0 de ${LESSONS.length} lições concluídas`)).toBeInTheDocument()
    for (const lesson of LESSONS) {
      expect(screen.getByRole('button', { name: new RegExp(lesson.title) })).toBeInTheDocument()
    }
  })

  it('opens a lesson, gives feedback on the exercise and saves progress', () => {
    render(<Learn onBack={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /Golpe do falso parente/ }))

    expect(screen.getByRole('heading', { level: 1, name: 'Golpe do falso parente' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Sinais de alerta' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'É golpe' }))
    expect(screen.getByRole('status')).toHaveTextContent('Isso mesmo! É golpe.')
    expect(loadLessonProgress()).toEqual(['falso-parente'])

    fireEvent.click(screen.getByRole('button', { name: 'Próxima lição' }))
    expect(screen.getByRole('heading', { level: 1, name: 'Falsa central do banco' })).toBeInTheDocument()
  })

  it('explains gently when the answer is wrong', () => {
    render(<Learn onBack={() => {}} initialLessonId="mensagens-normais" />)
    fireEvent.click(screen.getByRole('button', { name: 'É golpe' }))
    expect(screen.getByRole('status')).toHaveTextContent('Quase. Provavelmente não é golpe.')
  })

  it('goes back from the lesson list', () => {
    const onBack = vi.fn()
    render(<Learn onBack={onBack} />)
    fireEvent.click(screen.getByRole('button', { name: 'Voltar' }))
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
    const text = lessonSpeechText(LESSONS[0])
    expect(text.startsWith('Golpe do falso parente')).toBe(true)
    expect(text.indexOf('Sinais de alerta:')).toBeLessThan(text.indexOf('O que fazer:'))
    expect(text).toContain(LESSONS[0].doThis[0])
  })
})
