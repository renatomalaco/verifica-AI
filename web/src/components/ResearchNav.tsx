import { canRunStudy, lastAccessDay } from '../domain/researchAccess'
import { useStudyRun, type StudyRun } from '../hooks/useStudyRun'
import { m } from '../paraglide/messages.js'
import type { ResearchRole, ResearchUser } from '../types'

interface Props {
  user: ResearchUser
  onSignOut: () => void
  onStudyRan: () => void
  onSignedOut: () => void
}

const ROLE_LABELS: Record<ResearchRole, () => string> = {
  admin: m.research_role_admin,
  researcher: m.research_role_researcher,
}

const RUN_STATUS: Partial<Record<StudyRun, () => string>> = {
  running: m.research_nav_running,
  done: m.research_nav_run_done,
  failed: m.research_nav_run_failed,
}

// Side navigation of the research area: it exists only for a signed-in account.
export function ResearchNav({ user, onSignOut, onStudyRan, onSignedOut }: Props) {
  return (
    <nav className="research-nav card stack" aria-label={m.research_nav_label()}>
      <div className="stack">
        <p className="text-small">{m.research_nav_signed_in_as({ email: user.email })}</p>
        <p className="text-small text-muted">
          {ROLE_LABELS[user.role]()}
          {user.expires_at && ` · ${m.research_nav_expires({ date: lastAccessDay(user.expires_at).toLocaleDateString() })}`}
        </p>
      </div>

      <ul className="research-nav__list">
        <li>
          <a href="/pesquisa" aria-current="page">
            {m.research_nav_report()}
          </a>
        </li>
        <li>
          <a href="/metrics" target="_blank" rel="noopener">
            {m.research_nav_metrics()}
          </a>
        </li>
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
