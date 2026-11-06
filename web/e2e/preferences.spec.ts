import { expect, test, type Page } from '@playwright/test'
import { m } from '../src/paraglide/messages.js'
import { DEFAULT_PREFERENCES } from '../src/prefs/preferences'
import { mockScan, prepare, verdict } from './support'

async function showVerdict(page: Page) {
  await mockScan(page, verdict('GOLPE'))
  await page.goto('/')
  await page.getByLabel(m.home_text_label()).fill('Oi mãe, troquei de número')
  await page.getByRole('button', { name: m.home_check_now() }).click()
  return page.getByRole('heading', { level: 1, name: m.verdict_title_scam() })
}

// Longest animation or transition on the page, in milliseconds.
function longestMotionMs(page: Page): Promise<number> {
  return page.evaluate(() => {
    const ms = (value: string) => Math.max(...value.split(',').map((v) => parseFloat(v) * (v.trim().endsWith('ms') ? 1 : 1000)))
    return Math.max(
      0,
      ...[...document.querySelectorAll('*')].map((el) => {
        const style = getComputedStyle(el)
        return Math.max(ms(style.animationDuration), ms(style.transitionDuration))
      })
    )
  })
}

test('the system "reduce motion" setting is followed when the person chose "system"', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await prepare(page, { ...DEFAULT_PREFERENCES, motion: 'system' })

  await expect(await showVerdict(page)).toBeVisible()

  expect(await longestMotionMs(page)).toBeLessThanOrEqual(10)
})

test('"less motion" from the catalog stops animations even when the system allows them', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await prepare(page, { ...DEFAULT_PREFERENCES, motion: 'reduced' })

  await expect(await showVerdict(page)).toBeVisible()

  expect(await longestMotionMs(page)).toBeLessThanOrEqual(10)
})

test('high contrast and larger text from the catalog reach the page', async ({ page }) => {
  await prepare(page, { ...DEFAULT_PREFERENCES, highContrast: true, textSize: 'xlarge' })
  await page.goto('/')

  const html = page.locator('html')
  await expect(html).toHaveAttribute('data-contrast', 'high')
  await expect(html).toHaveAttribute('data-text-size', 'xlarge')
  const bodySize = await page.evaluate(() => parseFloat(getComputedStyle(document.body).fontSize))
  expect(bodySize).toBeGreaterThan(18)
})

test('situations chosen for someone else configure the phone and survive a reload', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: m.onboarding_who_someone_else() }).click()
  await page.getByRole('button', { name: new RegExp(m.settings_situation_vision_title()) }).click()
  await page.getByRole('button', { name: m.onboarding_catalog_apply() }).click()

  await expect(page.locator('html')).toHaveAttribute('data-contrast', 'high')
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-contrast', 'high')
})
