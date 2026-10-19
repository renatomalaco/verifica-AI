import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Privacy } from './Privacy'
import { PreferencesProvider } from '../prefs/PreferencesProvider'

describe('Privacy', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('explains what is not stored and why anonymous records are kept for research', () => {
    render(<Privacy onBack={() => {}} />)
    expect(screen.getByRole('heading', { level: 1, name: 'Como o Verifica cuida dos seus dados' })).toHaveFocus()
    expect(screen.getByText('O texto, o link ou o print que você colou.')).toBeInTheDocument()
    expect(screen.getByText(/alimentam as métricas do modo pesquisa/)).toBeInTheDocument()
    expect(screen.getByText(/no máximo 1 hora/)).toBeInTheDocument()
  })

  it('erases what the Verifica saved on this device', () => {
    localStorage.setItem('vf.onboarded', '1')
    localStorage.setItem('vf.lessons', '["falso-parente"]')
    localStorage.setItem('outro.app', 'fica')
    render(
      <PreferencesProvider>
        <Privacy onBack={() => {}} />
      </PreferencesProvider>
    )
    fireEvent.click(screen.getByRole('button', { name: 'Apagar dados deste aparelho' }))
    expect(screen.getByRole('status')).toHaveTextContent('foram apagados')
    expect(localStorage.getItem('vf.onboarded')).toBeNull()
    expect(localStorage.getItem('vf.lessons')).toBeNull()
    expect(localStorage.getItem('outro.app')).toBe('fica')
  })

  it('goes back', () => {
    const onBack = vi.fn()
    render(<Privacy onBack={onBack} />)
    fireEvent.click(screen.getByRole('button', { name: 'Voltar' }))
    expect(onBack).toHaveBeenCalledTimes(1)
  })
})
