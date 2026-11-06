import { describe, expect, it } from 'vitest'
import { pickVoice } from './voice'

const voice = (name: string, lang: string) => ({ name, lang })

// Lists like the ones real browsers report (names trimmed).
const WINDOWS_EDGE = [
  voice('Microsoft Maria - Portuguese (Brazil)', 'pt-BR'),
  voice('Microsoft Zira - English (United States)', 'en-US'),
  voice('Microsoft Francisca Online (Natural) - Portuguese (Brazil)', 'pt-BR'),
  voice('Microsoft Antonio Online (Natural) - Portuguese (Brazil)', 'pt-BR'),
]
const ANDROID_CHROME = [voice('English United States', 'en_US'), voice('Português Brasil', 'pt_BR')]
const CHROME_DESKTOP = [voice('Microsoft Maria - Portuguese (Brazil)', 'pt-BR'), voice('Google português do Brasil', 'pt-BR')]
const MAC_SAFARI = [voice('Luciana', 'pt-BR'), voice('Luciana (Enhanced)', 'pt-BR'), voice('Joana', 'pt-PT')]

describe('pickVoice', () => {
  it('prefers a natural (neural) Brazilian voice over the robotic default', () => {
    expect(pickVoice(WINDOWS_EDGE)?.name).toBe('Microsoft Francisca Online (Natural) - Portuguese (Brazil)')
  })

  it('treats Google and enhanced voices as natural', () => {
    expect(pickVoice(CHROME_DESKTOP)?.name).toBe('Google português do Brasil')
    expect(pickVoice(MAC_SAFARI)?.name).toBe('Luciana (Enhanced)')
  })

  it('accepts the underscore language tags Android reports', () => {
    expect(pickVoice(ANDROID_CHROME)?.name).toBe('Português Brasil')
  })

  it('falls back to European Portuguese before any other language', () => {
    expect(pickVoice([voice('Samantha', 'en-US'), voice('Joana', 'pt-PT')])?.name).toBe('Joana')
  })

  it('prefers Brazilian Portuguese even when only the European voice is natural', () => {
    expect(pickVoice([voice('Duarte Online (Natural)', 'pt-PT'), voice('Maria', 'pt-BR')])?.name).toBe('Maria')
  })

  it('leaves the choice to the browser when there is no Portuguese voice', () => {
    expect(pickVoice([voice('Samantha', 'en-US')])).toBeNull()
    expect(pickVoice([])).toBeNull()
  })
})
