import { explainsWithoutLimit } from '../domain/researchAccess'
import { m } from '../paraglide/messages.js'
import type { ResearchRole } from '../types'

interface Props {
  role: ResearchRole
  onBack: () => void
}

// For a role with neither the study nor accounts (a family account): what the account allows.
export function ResearchAccountPage({ role, onBack }: Props) {
  return (
    <section className="app-main" aria-labelledby="conta-titulo">
      <header className="stack">
        <p className="text-small text-muted">{m.research_area()}</p>
        <h1 className="title-l" id="conta-titulo">
          {m.research_account_title()}
        </h1>
        <p>{explainsWithoutLimit(role) ? m.research_account_unlimited_explain() : m.research_account_nothing_yet()}</p>
      </header>
      <button type="button" className="btn btn-solid" onClick={onBack}>
        {m.research_account_back()}
      </button>
    </section>
  )
}
