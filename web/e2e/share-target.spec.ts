import { expect, test, type Page } from '@playwright/test'
import { m } from '../src/paraglide/messages.js'
import { mockScan, prepare, verdict } from './support'

// The share target is handled by the service worker, so this suite lets it run.
test.use({ serviceWorkers: 'allow' })

// 1x1 PNG: enough for the app to accept the file and send it.
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
  'base64'
)

async function waitForServiceWorker(page: Page): Promise<void> {
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready
    if (navigator.serviceWorker.controller) return
    await new Promise((resolve) => navigator.serviceWorker.addEventListener('controllerchange', resolve, { once: true }))
  })
}

/**
 * Does what Android does when the person shares into the installed app: a multipart POST to the
 * manifest's action, answered by the service worker. It is sent with fetch and the redirect is then
 * opened, because Playwright never sees a POST navigation answered by a service worker finish.
 */
async function shareIntoApp(page: Page, fields: Record<string, string>, image?: Buffer): Promise<void> {
  const redirectedTo = await page.evaluate(
    async ({ entries, png }) => {
      const form = new FormData()
      Object.entries(entries).forEach(([name, value]) => form.append(name, value))
      if (png) form.append('image', new File([Uint8Array.from(atob(png), (c) => c.charCodeAt(0))], 'print.png', { type: 'image/png' }))
      const response = await fetch('/share-target', { method: 'POST', body: form })
      return response.url
    },
    { entries: fields, png: image?.toString('base64') }
  )
  expect(new URL(redirectedTo).search).toBe('?compartilhado=1')
  await page.goto(redirectedTo)
}

test.beforeEach(async ({ page }) => {
  await prepare(page)
  await page.goto('/')
  await waitForServiceWorker(page)
})

test('a screenshot shared from another app opens ready to check', async ({ page }) => {
  const sent = await mockScan(page, verdict('GOLPE', 'imagem'))

  await shareIntoApp(page, {}, PNG)

  await expect(page.getByRole('tab', { name: m.home_tab_image() })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByAltText(m.home_image_preview_alt())).toBeVisible()
  expect(new URL(page.url()).search).toBe('')

  await page.getByRole('button', { name: m.home_check_now() }).click()
  await expect(page.getByRole('heading', { level: 1, name: m.verdict_title_scam() })).toBeFocused()
  expect(sent().image_b64).toBe(PNG.toString('base64'))
})

test('a link shared from another app opens in the link tab', async ({ page }) => {
  await shareIntoApp(page, { title: 'Promoção', url: 'https://bb-atualizacao.top/login' })

  await expect(page.getByRole('tab', { name: m.home_tab_url() })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByLabel(m.home_url_label())).toHaveValue('https://bb-atualizacao.top/login')
})

test('the shared screenshot is erased from the device once the app takes it', async ({ page }) => {
  await shareIntoApp(page, {}, PNG)
  await expect(page.getByAltText(m.home_image_preview_alt())).toBeVisible()

  const stillStored = await page.evaluate(async () => (await caches.open('verifica-share')).keys().then((keys) => keys.length))
  expect(stillStored).toBe(0)
})
