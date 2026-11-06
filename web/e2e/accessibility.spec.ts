import { expect, test, type Page } from '@playwright/test'
import { m } from '../src/paraglide/messages.js'
import { MODES, axeViolations, mockScan, mockSignedOut, prepare, verdict } from './support'

// Full WCAG 2.2 AA in a real browser (contrast and target size included), in both modes.
const SCREENS: Record<string, (page: Page) => Promise<void>> = {
  home: async (page) => {
    await page.goto('/')
  },
  verdict: async (page) => {
    await mockScan(page, verdict('GOLPE'))
    await page.goto('/')
    await page.getByLabel(m.home_text_label()).fill('Oi mãe, troquei de número')
    await page.getByRole('button', { name: m.home_check_now() }).click()
    await page.getByRole('heading', { level: 1, name: m.verdict_title_scam() }).waitFor()
  },
  settings: async (page) => {
    await page.goto('/')
    await page.getByRole('button', { name: m.common_reading_settings() }).click()
  },
  course: async (page) => {
    await page.goto('/aprender')
  },
  privacy: async (page) => {
    await page.goto('/privacidade')
  },
  'research sign-in': async (page) => {
    await mockSignedOut(page)
    await page.goto('/pesquisa')
    await page.getByRole('heading', { name: m.research_login_title() }).waitFor()
  },
}

for (const [mode, prefs] of Object.entries(MODES)) {
  test.describe(`${mode} mode`, () => {
    for (const [name, open] of Object.entries(SCREENS)) {
      test(`${name} meets WCAG 2.2 AA`, async ({ page }) => {
        await prepare(page, prefs)
        await open(page)
        expect(await axeViolations(page)).toEqual([])
      })
    }
  })
}

test('first visit meets WCAG 2.2 AA', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('heading', { name: m.onboarding_welcome_title() }).waitFor()
  expect(await axeViolations(page)).toEqual([])
})
