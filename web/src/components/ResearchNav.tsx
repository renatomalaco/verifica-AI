import type { MouseEvent } from 'react'
import {
  ACCOUNTS_PATH,
  REPORT_PATH,
  canManageAccounts,
  canRunStudy,
  lastAccessDay,
  type ResearchSection,
} from '../domain/researchAccess'
import { useStudyRun, type StudyRun } from '../hooks/useStudyRun'
import { m } from '../paraglide/messages.js'
import type { ResearchUser } from '../types'

interface Props {
  user: ResearchUser
  section: ResearchSection
  onNavigate: (path: string) => void
  onSignOut: () => void
  onStudyRan: () => void
  onSignedOut: () => void
}

const RUN_STATUS: Partial<Record<StudyRun, () => string>> = {
  running: m.research_nav_running,
  done: m.research_nav_run_done,
  failed: m.research_nav_run_failed,
}

// Side navigation of the research area: it exists only for a signed-in account.
export function ResearchNav({ user, section, onNavigate, onSignOut, onStudyRan, onSignedOut }: Props) {
  // Real links (they open in a new tab too), but a plain click switches the screen without reloading.
  const follow = (path: string) => (event: MouseEvent) => {
    event.preventDefault()
    onNavigate(path)
  }
  const current = (target: ResearchSection) => (section === target ? 'page' : undefined)

  return (
    <nav className="research-nav card stack" aria-label={m.research_nav_label()}>
      <div className="stack">
        <p className="text-small">{m.research_nav_signed_in_as({ email: user.email })}</p>
        <p className="text-small text-muted">
          {user.role.name}
          {user.expires_at && ` · ${m.research_nav_expires({ date: lastAccessDay(user.expires_at).toLocaleDateString() })}`}
        </p>
      </div>

      <ul className="research-nav__list">
        <li>
          <a href={REPORT_PATH} aria-current={current('report')} onClick={follow(REPORT_PATH)}>
            {m.research_nav_report()}
          </a>
        </li>
        {canManageAccounts(user.role) && (
          <li>
            <a href={ACCOUNTS_PATH} aria-current={current('accounts')} onClick={follow(ACCOUNTS_PATH)}>
              {m.research_nav_accounts()}
            </a>
          </li>
        )}
      </ul>

      {canRunStudy(user.role) && <RunStudy onStudyRan={onStudyRan} onSignedOut={onSignedOut} />}

      <button type="button" className="btn btn-outline" onClick={onSignOut}>
        {m.research_nav_sign_out()}
      </button>
    </nav>
  )
}

function RunStudy({ onStudyRan, onSignedOut }: Pick<Props, 'onStudyRan' | 'onSignedOut'>) {
  const { state, run } = useStudyRun(onStudyRan, onSignedOut)
  const status = RUN_STATUS[state]

  return (
    <div className="stack">
      <button type="button" className="btn btn-solid" onClick={run} disabled={state === 'running'}>
        {m.research_nav_run()}
      </button>
      <p className="text-small" role="status">
        {status?.()}
      </p>
    </div>
  )
}
