import { describe, expect, it } from 'vitest'
import { pickVoice, planRecordings, recordingFile, recordingKey } from './voice'

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

describe('recordingKey', () => {
  it('is stable for the same text and locale', () => {
    expect(recordingKey('pt-BR', 'Isto é um golpe.')).toBe(recordingKey('pt-BR', 'Isto é um golpe.'))
  })

  it('changes when the text or the locale changes', () => {
    const key = recordingKey('pt-BR', 'Isto é um golpe.')
    expect(recordingKey('pt-BR', 'Isto é um golpe!')).not.toBe(key)
    expect(recordingKey('pt-PT', 'Isto é um golpe.')).not.toBe(key)
  })

  it('is safe to use as a file name', () => {
    expect(recordingKey('pt-BR', 'Cuidado: pode ser golpe.')).toMatch(/^[0-9a-f]+$/)
  })
})

describe('recordingFile', () => {
  const recorded = new Set([recordingKey('pt-BR', 'Isto é um golpe.')])

  it('points to the recording of a recorded text', () => {
    expect(recordingFile(recorded, 'pt-BR', 'Isto é um golpe.')).toBe(`voice/${recordingKey('pt-BR', 'Isto é um golpe.')}.mp3`)
  })

  it('has no recording for a text that was never recorded', () => {
    expect(recordingFile(recorded, 'pt-BR', 'Texto novo.')).toBeNull()
  })

  it('has no recording for the same text in another locale', () => {
    expect(recordingFile(recorded, 'pt-PT', 'Isto é um golpe.')).toBeNull()
  })
})

describe('planRecordings', () => {
  const recording = (text: string) => ({ key: recordingKey('pt-BR', text), locale: 'pt-BR', text })
  const OLD = recording('Texto antigo.')
  const KEPT = recording('Texto igual.')
  const NEW = recording('Texto novo.')
  const VOICE = { model: 'gemini-tts', voice: 'Sulafat' }
  const previous = { ...VOICE, keys: [OLD.key, KEPT.key] }

  it('records only the texts that are not recorded yet', () => {
    const plan = planRecordings(previous, VOICE, [KEPT, NEW])
    expect(plan.keep).toEqual([KEPT.key])
    expect(plan.render).toEqual([NEW])
  })

  it('drops recordings of texts that are no longer spoken', () => {
    expect(planRecordings(previous, VOICE, [NEW]).keep).toEqual([])
  })

  it('records everything again when the model or the voice changes', () => {
    expect(planRecordings(previous, { ...VOICE, voice: 'Kore' }, [KEPT, NEW])).toEqual({ keep: [], render: [KEPT, NEW] })
    expect(planRecordings(previous, { ...VOICE, model: 'other' }, [KEPT]).render).toEqual([KEPT])
  })

  it('records a text spoken in two places only once', () => {
    expect(planRecordings(previous, VOICE, [NEW, NEW]).render).toEqual([NEW])
  })
})
