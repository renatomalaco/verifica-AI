import { afterEach, describe, expect, it, vi } from 'vitest'
import { SHARE_CACHE, SHARE_KEY, takeShared } from './shareInbox'

// Minimal Cache Storage: one cache holding what the service worker stored.
function fakeCaches(stored: Map<string, Response>) {
  const cache = {
    match: vi.fn(async (key: string) => stored.get(key)),
    delete: vi.fn(async (key: string) => stored.delete(key)),
  }
  return { open: vi.fn(async () => cache), cache }
}

const formResponse = (body: string) =>
  new Response(body, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })

describe('takeShared', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns what the service worker received and erases it from the device', async () => {
    const stored = new Map([[SHARE_KEY, formResponse('text=Seu+CPF+foi+bloqueado')]])
    const caches = fakeCaches(stored)
    vi.stubGlobal('caches', caches)

    const form = await takeShared()

    expect(caches.open).toHaveBeenCalledWith(SHARE_CACHE)
    expect(form?.get('text')).toBe('Seu CPF foi bloqueado')
    expect(stored.size).toBe(0)
  })

  it('returns nothing when nothing was shared', async () => {
    vi.stubGlobal('caches', fakeCaches(new Map()))
    expect(await takeShared()).toBeNull()
  })

  it('returns nothing on browsers without Cache Storage', async () => {
    vi.stubGlobal('caches', undefined)
    expect(await takeShared()).toBeNull()
  })
})
