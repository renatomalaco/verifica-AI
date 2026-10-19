import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { InputTabs } from './InputTabs'
import { MAX_IMAGE_BYTES } from '../domain/image'
import type { InputTab } from '../types'

function setup(overrides: Partial<Parameters<typeof InputTabs>[0]> = {}) {
  const props = {
    tab: 'text' as InputTab,
    onTabChange: vi.fn(),
    content: '',
    onContentChange: vi.fn(),
    imageB64: null,
    onImageChange: vi.fn(),
    onScan: vi.fn(),
    ...overrides,
  }
  render(<InputTabs {...props} />)
  return props
}

describe('InputTabs', () => {
  it('keeps the main action disabled until something is pasted', () => {
    setup()
    expect(screen.getByRole('button', { name: 'Conferir agora' })).toBeDisabled()
  })

  it('enables the main action and triggers the scan', () => {
    const props = setup({ content: 'Oi mãe' })
    const btn = screen.getByRole('button', { name: 'Conferir agora' })
    expect(btn).toBeEnabled()
    fireEvent.click(btn)
    expect(props.onScan).toHaveBeenCalledTimes(1)
  })

  it('switches tabs by click and by arrow keys', () => {
    const props = setup()
    fireEvent.click(screen.getByRole('tab', { name: 'Link' }))
    expect(props.onTabChange).toHaveBeenCalledWith('url')
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Mensagem' }), { key: 'ArrowLeft' })
    expect(props.onTabChange).toHaveBeenCalledWith('image')
  })

  it('labels the field for the selected tab', () => {
    setup({ tab: 'url' })
    expect(screen.getByLabelText('Cole o endereço do site')).toHaveAttribute('type', 'url')
  })

  it('rejects images that are too large with a friendly message', () => {
    const props = setup({ tab: 'image' })
    const input = screen.getByLabelText('Envie a foto ou o print da tela') as HTMLInputElement
    const big = new File(['x'], 'print.png', { type: 'image/png' })
    Object.defineProperty(big, 'size', { value: MAX_IMAGE_BYTES + 1 })
    fireEvent.change(input, { target: { files: [big] } })
    expect(screen.getByRole('alert')).toHaveTextContent(/grande demais/)
    expect(props.onImageChange).not.toHaveBeenCalled()
  })

  it('rejects files that are not images', () => {
    setup({ tab: 'image' })
    const input = screen.getByLabelText('Envie a foto ou o print da tela') as HTMLInputElement
    fireEvent.change(input, { target: { files: [new File(['x'], 'a.pdf', { type: 'application/pdf' })] } })
    expect(screen.getByRole('alert')).toHaveTextContent(/PNG, JPEG ou WebP/)
  })
})
