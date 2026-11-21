import { describe, expect, it, vi } from 'vitest'
import { shareWithFamily } from './share'

const TEXT = 'Recebi uma mensagem suspeita.'
const WHATSAPP = `https://wa.me/?text=${encodeURIComponent(TEXT)}`

describe('shareWithFamily', () => {
  it('opens the phone share sheet when there is one', async () => {
    const share = vi.fn().mockResolvedValue(undefined)
    const open = vi.fn()

    expect(await shareWithFamily(TEXT, { share } as unknown as Navigator, open)).toBe('shared')
    expect(share).toHaveBeenCalledWith({ text: TEXT })
    expect(open).not.toHaveBeenCalled()
  })

  it('does nothing else when the person closes the share sheet', async () => {
    const share = vi.fn().mockRejectedValue(new DOMException('cancelled', 'AbortError'))
    const open = vi.fn()

    expect(await shareWithFamily(TEXT, { share } as unknown as Navigator, open)).toBe('cancelled')
    expect(open).not.toHaveBeenCalled()
  })

  it.each([
    ['there is no share sheet', {}],
    ['the share sheet fails', { share: vi.fn().mockRejectedValue(new Error('not allowed')) }],
  ])('opens WhatsApp with the message ready when %s', async (_, nav) => {
    const open = vi.fn()

    expect(await shareWithFamily(TEXT, nav as Navigator, open)).toBe('whatsapp')
    expect(open).toHaveBeenCalledWith(WHATSAPP, '_blank', 'noopener')
  })
})
