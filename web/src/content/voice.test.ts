import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

// Product voice rule (PRODUCT.md): third person or impersonal, never "I" or "we".
const FIRST_PERSON = /\b(eu|me desculpe|meu|minha|nós|nosso|nossa|encontramos|detectamos|verificamos|analisamos|podemos)\b/i

// Answers the person gives in their own voice, not the product speaking.
const PERSON_ANSWERS = new Set(['onboarding_who_self'])

const MESSAGES_DIR = join(__dirname, '../../messages/pt-BR')

function allStrings(value: unknown): string[] {
  if (typeof value === 'string') return [value]
  if (Array.isArray(value)) return value.flatMap(allStrings)
  if (value && typeof value === 'object') return Object.values(value).flatMap(allStrings)
  return []
}

describe('message dictionary voice', () => {
  const files = readdirSync(MESSAGES_DIR).filter((f) => f.endsWith('.json'))

  it.each(files)('%s never speaks in the first person', (file) => {
    const json = JSON.parse(readFileSync(join(MESSAGES_DIR, file), 'utf-8'))
    delete json.$schema
    for (const key of PERSON_ANSWERS) delete json[key]
    const offenders = allStrings(json).filter((text) => FIRST_PERSON.test(text))
    expect(offenders).toEqual([])
  })
})
