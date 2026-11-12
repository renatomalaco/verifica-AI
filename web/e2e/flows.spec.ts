import { expect, test } from '@playwright/test'
import { m } from '../src/paraglide/messages.js'
import { mockScan, prepare, verdict } from './support'

// 1x1 PNG: enough for the app to accept the file and send it.
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
  'base64'
)

test.beforeEach(async ({ page }) => {
  await prepare(page)
})

test('a pasted message gets a verdict, with focus on its title', async ({ page }) => {
  const sent = await mockScan(page, verdict('GOLPE'))
  await page.goto('/')

  await page.getByLabel(m.home_text_label()).fill('Oi mãe, troquei de número. Me manda um pix?')
  await page.getByRole('button', { name: m.home_check_now() }).click()

  const title = page.getByRole('heading', { level: 1, name: m.verdict_title_scam() })
  await expect(title).toBeVisible()
  await expect(title).toBeFocused()
  expect(sent()).toEqual({ content: 'Oi mãe, troquei de número. Me manda um pix?', image_b64: null })
})

test('a link is checked from its own tab', async ({ page }) => {
  const sent = await mockScan(page, verdict('CUIDADO', 'url'))
  await page.goto('/')

  await page.getByRole('tab', { name: m.home_tab_url() }).click()
  await expect(page.getByRole('tab', { name: m.home_tab_url() })).toHaveAttribute('aria-selected', 'true')
  await page.getByLabel(m.home_url_label()).fill('https://bb-atualizacao.top/login')
  await page.getByRole('button', { name: m.home_check_now() }).click()

  await expect(page.getByRole('heading', { level: 1, name: m.verdict_title_caution() })).toBeFocused()
  expect(sent().content).toBe('https://bb-atualizacao.top/login')
})

test('a screenshot is sent as an image', async ({ page }) => {
  const sent = await mockScan(page, verdict('INCONCLUSIVO', 'imagem'))
  await page.goto('/')

  await page.getByRole('tab', { name: m.home_tab_image() }).click()
  await page.locator('input[type="file"]').setInputFiles({ name: 'print.png', mimeType: 'image/png', buffer: PNG })
  await page.getByRole('button', { name: m.home_check_now() }).click()

  await expect(page.getByRole('heading', { level: 1, name: m.verdict_title_inconclusive() })).toBeFocused()
  expect(sent().image_b64).toBe(PNG.toString('base64'))
})

test('the tabs follow the ARIA keyboard pattern', async ({ page }) => {
  await page.goto('/')

  await page.getByRole('tab', { name: m.home_tab_text() }).focus()
  await page.keyboard.press('ArrowRight')

  await expect(page.getByRole('tab', { name: m.home_tab_url() })).toBeFocused()
  await expect(page.getByRole('tab', { name: m.home_tab_url() })).toHaveAttribute('aria-selected', 'true')
})

test('too many scans in a row: the person is told about the short pause and can retry', async ({ page }) => {
  await page.route('**/api/v1/scans/stream', (route) =>
    route.fulfill({
      status: 429,
      contentType: 'application/json',
      headers: { 'Retry-After': '30' },
      body: JSON.stringify({ code: 'scan_rate_limited', retry_at: '2026-11-10T17:32:00Z' }),
    })
  )
  await page.goto('/')

  await page.getByLabel(m.home_text_label()).fill('Oi mãe, troquei de número. Me manda um pix?')
  await page.getByRole('button', { name: m.home_check_now() }).click()

  const alert = page.getByRole('alert')
  await expect(alert).toContainText('Foram muitas verificações seguidas nesta conexão')
  await expect(alert).toContainText(/Tente de novo a partir das \d{2}:\d{2}/)
  await expect(page.getByRole('button', { name: m.common_retry() })).toBeVisible()
})
