import { describe, expect, it } from 'vitest'
import { buildEvidence, friendlyErrorMessage, toScanRequest, upsertStage } from './investigation'

describe('buildEvidence', () => {
  it('uses the trimmed text for messages and links', () => {
    expect(buildEvidence('text', '  Oi mãe  ', null)).toEqual({ tab: 'text', content: 'Oi mãe', imageB64: null })
    expect(buildEvidence('url', 'golpe.com', 'data:image/png;base64,AAA')).toEqual({ tab: 'url', content: 'golpe.com', imageB64: null })
  })

  it('uses only the image on the photo tab', () => {
    expect(buildEvidence('image', 'texto esquecido', 'data:image/png;base64,AAA')).toEqual({
      tab: 'image',
      content: '',
      imageB64: 'data:image/png;base64,AAA',
    })
  })

  it('returns null when there is nothing to investigate', () => {
    expect(buildEvidence('text', '   ', null)).toBeNull()
    expect(buildEvidence('image', '', null)).toBeNull()
  })
})

describe('toScanRequest', () => {
  it('sends the image without the data URL prefix', () => {
    expect(toScanRequest({ tab: 'image', content: '', imageB64: 'data:image/webp;base64,QUJD' })).toEqual({
      content: '',
      image_b64: 'QUJD',
    })
    expect(toScanRequest({ tab: 'text', content: 'Oi', imageB64: null })).toEqual({ content: 'Oi', image_b64: null })
  })
})

describe('upsertStage', () => {
  it('adds new stages in arrival order and updates existing ones', () => {
    const started = upsertStage([], { stage: 'triage', status: 'started' })
    const both = upsertStage(started, { stage: 'stage_0_cache', status: 'started' })
    const updated = upsertStage(both, { stage: 'triage', status: 'done' })
    expect(updated).toEqual([
      { stage: 'triage', status: 'done' },
      { stage: 'stage_0_cache', status: 'started' },
    ])
    expect(started).toEqual([{ stage: 'triage', status: 'started' }])
  })
})

describe('friendlyErrorMessage', () => {
  it('talks about the internet when the connection failed', () => {
    expect(friendlyErrorMessage(new Error('Failed to fetch'), true)).toMatch(/internet caiu/)
    expect(friendlyErrorMessage(new Error('qualquer coisa'), false)).toMatch(/internet caiu/)
  })

  it('never exposes technical details for other failures', () => {
    const message = friendlyErrorMessage(new Error('Erro (500): Traceback ...'), true)
    expect(message).toBe('Houve um problema na investigação. Tente de novo em instantes.')
  })
})
