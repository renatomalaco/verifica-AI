import { describe, expect, it } from 'vitest'
import { sharedContent } from './share'

const form = (entries: Record<string, string | File>) => {
  const data = new FormData()
  Object.entries(entries).forEach(([name, value]) => data.append(name, value))
  return data
}

const screenshot = (size = 3) => new File([new Uint8Array(size)], 'print.png', { type: 'image/png' })

describe('sharedContent', () => {
  it('opens a shared screenshot in the photo tab', () => {
    const file = screenshot()
    expect(sharedContent(form({ image: file, text: 'veja isso' }))).toEqual({ tab: 'image', file })
  })

  it('prefers the shared link over the text around it', () => {
    expect(sharedContent(form({ url: 'https://golpe.example', text: 'olha' }))).toEqual({
      tab: 'url',
      content: 'https://golpe.example',
    })
  })

  it('takes the message text, or the title when there is no text', () => {
    expect(sharedContent(form({ text: 'Seu CPF foi bloqueado', title: 'Aviso' }))).toEqual({
      tab: 'text',
      content: 'Seu CPF foi bloqueado',
    })
    expect(sharedContent(form({ title: 'Aviso' }))).toEqual({ tab: 'text', content: 'Aviso' })
  })

  it('reads deep links the same way as shares', () => {
    expect(sharedContent(new URLSearchParams('url=https%3A%2F%2Fgolpe.example'))).toEqual({
      tab: 'url',
      content: 'https://golpe.example',
    })
  })

  it('ignores empty files and blank fields', () => {
    expect(sharedContent(form({ image: screenshot(0), url: '  ', text: '' }))).toBeNull()
    expect(sharedContent(new URLSearchParams())).toBeNull()
  })
})
