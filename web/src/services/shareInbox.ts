// Must match public/sw.js, which stores each share received on /share-target here.
export const SHARE_CACHE = 'verifica-share'
export const SHARE_KEY = '/share-target/last'

/** Takes what was shared into the app and erases it from the device right away. */
export async function takeShared(): Promise<FormData | null> {
  if (typeof caches === 'undefined') return null
  const cache = await caches.open(SHARE_CACHE)
  const response = await cache.match(SHARE_KEY)
  if (!response) return null
  await cache.delete(SHARE_KEY)
  return response.formData()
}
