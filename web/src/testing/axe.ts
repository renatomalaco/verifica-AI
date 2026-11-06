import axe from 'axe-core'

// WCAG 2.0 to 2.2, levels A and AA, plus axe's best practices.
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']

// jsdom draws nothing, so rules that need layout or pixels run only in the Playwright suite (e2e/).
const NEEDS_A_REAL_BROWSER = ['color-contrast', 'color-contrast-enhanced', 'target-size', 'scrollable-region-focusable']

/** Readable list of axe violations ("rule: selector"), empty when the markup is clean. */
export async function axeViolations(root: Element = document.body): Promise<string[]> {
  const rules = Object.fromEntries(NEEDS_A_REAL_BROWSER.map((id) => [id, { enabled: false }]))
  const results = await axe.run(root, { runOnly: { type: 'tag', values: TAGS }, rules })
  return results.violations.flatMap((v) => v.nodes.map((node) => `${v.id}: ${node.target.join(' ')}`))
}
