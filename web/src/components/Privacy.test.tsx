import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Privacy } from './Privacy'
import { m } from '../paraglide/messages.js'
import { PreferencesProvider } from '../prefs/PreferencesProvider'

describe('Privacy', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('explains what is not stored and why anonymous records are kept for research', () => {
    render(<Privacy onBack={() => {}} />)
    expect(screen.getByRole('heading', { level: 1, name: m.privacy_title() })).toHaveFocus()
    expect(screen.getByText(m.privacy_not_stored_content())).toBeInTheDocument()
    expect(screen.getByText(m.privacy_purpose_text())).toBeInTheDocument()
    expect(screen.getByText(m.privacy_quota_text())).toBeInTheDocument()
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
    fireEvent.click(screen.getByRole('button', { name: m.privacy_device_clear() }))
    expect(screen.getByRole('status')).toHaveTextContent(m.privacy_device_cleared())
    expect(localStorage.getItem('vf.onboarded')).toBeNull()
    expect(localStorage.getItem('vf.lessons')).toBeNull()
    expect(localStorage.getItem('outro.app')).toBe('fica')
  })

  it('goes back', () => {
    const onBack = vi.fn()
    render(<Privacy onBack={onBack} />)
    fireEvent.click(screen.getByRole('button', { name: m.common_back() }))
    expect(onBack).toHaveBeenCalledTimes(1)
  })
})
