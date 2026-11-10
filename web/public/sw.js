// v2: navigation is network-first (the app never gets stuck on an old version);
// the cache is used only when the person is offline.
const CACHE_NAME = 'verifica-ai-v2'
const STATIC_ASSETS = ['/', '/index.html', '/favicon.svg', '/manifest.json']
// Shares from other apps (Web Share Target) wait here until the app takes them.
// Must match src/services/shareInbox.ts and SHARED_FLAG in src/domain/share.ts.
const SHARE_CACHE = 'verifica-share'
const SHARE_KEY = '/share-target/last'
const SHARED_PAGE = '/?compartilhado=1'

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)))
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME && key !== SHARE_CACHE).map((key) => caches.delete(key))))
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method === 'POST' && new URL(request.url).pathname === '/share-target') {
    event.respondWith(receiveShare(request))
    return
  }
  if (request.method !== 'GET' || request.url.includes('/api/') || request.url.includes('/pesquisa/')) {
    return
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put('/index.html', copy))
          return response
        })
        .catch(() => caches.match('/index.html'))
    )
    return
  }

  event.respondWith(caches.match(request).then((cached) => cached || fetch(request)))
})

// The share arrives as a multipart POST that the app itself cannot read: keep the form
// (photo, text, link) on the device and open the app, which takes it and erases it.
async function receiveShare(request) {
  const form = await request.formData()
  const cache = await caches.open(SHARE_CACHE)
  await cache.put(SHARE_KEY, new Response(form))
  return Response.redirect(SHARED_PAGE, 303)
}
