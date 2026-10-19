import { describe, expect, it } from 'vitest'
import {
  adviceSteps,
  channelLabel,
  familyAlertText,
  offersScamHelp,
  remainingExplanationsText,
  spokenVerdictText,
  todoTitle,
  verdictTitle,
} from './verdict'
import type { ScanResponse } from '../types'

const scam: ScanResponse = {
  id: 'scan-1',
  threat_level: 'GOLPE',
  verdict_plain: 'Alguém está fingindo ser da sua família.',
  action_advice: 'Não mande Pix. Ligue para o seu filho.',
  details: { channel: 'texto', deciding_stage: 'triage', scores: {} },
}

describe('verdict copy', () => {
  it('names each verdict in plain, third-person language', () => {
    expect(verdictTitle('GOLPE')).toBe('Isto é um golpe.')
    expect(verdictTitle('CUIDADO')).toBe('Cuidado: pode ser golpe.')
    expect(verdictTitle('SEGURO')).toBe('Nenhum sinal de golpe encontrado.')
    expect(verdictTitle('INCONCLUSIVO')).toBe('Não deu para ter certeza.')
  })

  it('frames the advice according to how urgent it is', () => {
    expect(todoTitle('GOLPE')).toBe('Faça agora')
    expect(todoTitle('CUIDADO')).toBe('Faça agora')
    expect(todoTitle('SEGURO')).toBe('Mesmo assim')
    expect(todoTitle('INCONCLUSIVO')).toBe('Até ter certeza')
  })

  it('offers scam help only when there is a risk of having been scammed', () => {
    expect(offersScamHelp('GOLPE')).toBe(true)
    expect(offersScamHelp('CUIDADO')).toBe(true)
    expect(offersScamHelp('SEGURO')).toBe(false)
    expect(offersScamHelp('INCONCLUSIVO')).toBe(false)
  })

  it('splits advice into one step per sentence', () => {
    expect(adviceSteps('Não clique. Ligue para o banco! Tudo bem?')).toEqual(['Não clique.', 'Ligue para o banco!', 'Tudo bem?'])
  })

  it('builds the text read aloud and the alert sent to the family', () => {
    expect(spokenVerdictText(scam)).toBe(
      'Isto é um golpe. Alguém está fingindo ser da sua família. Faça agora: Não mande Pix. Ligue para o seu filho.'
    )
    expect(familyAlertText(scam)).toBe(
      'Verifica: Isto é um golpe.\n\nAlguém está fingindo ser da sua família.\n\nFaça agora: Não mande Pix. Ligue para o seu filho.'
    )
  })

  it('tells how many explanations are left today', () => {
    expect(remainingExplanationsText(2)).toBe('Você ainda pode pedir 2 explicações hoje.')
    expect(remainingExplanationsText(1)).toBe('Você ainda pode pedir 1 explicação hoje.')
    expect(remainingExplanationsText(0)).toBe('Esta foi a última explicação de hoje.')
  })

  it('describes the channel in everyday words', () => {
    expect(channelLabel('texto')).toBe('mensagem de texto')
    expect(channelLabel('url')).toBe('link')
    expect(channelLabel('imagem')).toBe('foto ou print')
  })
})
