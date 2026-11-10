// Set by the service worker on the address it opens after receiving a share (public/sw.js).
export const SHARED_FLAG = 'compartilhado'

export type SharedContent = { tab: 'image'; file: File } | { tab: 'text' | 'url'; content: string }

// FormData (Web Share Target POST) and URLSearchParams (deep links) both fit.
interface SharedFields {
  get(name: string): FormDataEntryValue | null
}

const filled = (value: FormDataEntryValue | null): string =>
  typeof value === 'string' ? value.trim() : ''

/** What another app shared, ready for its input tab; null when nothing usable came. */
export function sharedContent(fields: SharedFields): SharedContent | null {
  const image = fields.get('image')
  if (image instanceof File && image.size > 0) return { tab: 'image', file: image }

  const url = filled(fields.get('url'))
  if (url) return { tab: 'url', content: url }

  const text = filled(fields.get('text')) || filled(fields.get('title'))
  if (text) return { tab: 'text', content: text }
  return null
}
