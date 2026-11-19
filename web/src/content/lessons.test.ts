import { describe, expect, it } from 'vitest'
import { lessons } from './lessons'

const FEBRABAN_PAGE = /^https:\/\/portal\.febraban\.org\.br\/DetalheAntifraude\/\d+\/pt-br\/$/
// The only lesson that is not about a scam, so FEBRABAN has no page for it.
const NOT_A_SCAM = 'mensagens-normais'

describe('course content', () => {
  it('cites a FEBRABAN anti-fraud page in every lesson about a scam', () => {
    for (const lesson of lessons().filter((l) => l.id !== NOT_A_SCAM)) {
      expect(lesson.sources.length, lesson.id).toBeGreaterThan(0)
      for (const source of lesson.sources) expect(source.url, lesson.id).toMatch(FEBRABAN_PAGE)
    }
  })

  it('covers the scams FEBRABAN lists as the most common', () => {
    const cited = new Set(lessons().flatMap((l) => l.sources.map((s) => s.url)))
    // 15 cards on portal.febraban.org.br/AntiFraude ("Golpes mais comuns"), accessed 2026-11-18.
    for (const id of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 19]) {
      expect(cited, `card ${id}`).toContain(`https://portal.febraban.org.br/DetalheAntifraude/${id}/pt-br/`)
    }
  })

  it('keeps lesson ids unique, since progress is saved by id', () => {
    const ids = lessons().map((l) => l.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('keeps "Nem tudo é golpe" as the last lesson', () => {
    expect(lessons().at(-1)?.id).toBe(NOT_A_SCAM)
  })
})
