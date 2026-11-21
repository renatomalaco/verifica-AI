import { useState } from 'react'
import { researchSection } from '../domain/researchAccess'
import { useResearchSession } from '../hooks/useResearchSession'
import { m } from '../paraglide/messages.js'
import { ResearchAblationView } from './ResearchAblationView'
import { ResearchAccountPage } from './ResearchAccountPage'
import { ResearchAccounts } from './ResearchAccounts'
import { ResearchLogin } from './ResearchLogin'
import { ResearchNav } from './ResearchNav'

interface Props {
  onBack: () => void
}

// Gate of the research area (R5a): nothing of the study shows up without a signed-in account.
export function ResearchArea({ onBack }: Props) {
  const { session, signedIn, signOut, sessionEnded } = useResearchSession()
  const [reportVersion, setReportVersion] = useState(0)
  const [path, setPath] = useState(window.location.pathname)

  const navigate = (next: string) => {
    window.history.pushState(null, '', next)
    setPath(next)
  }

  if (session.status === 'checking') {
    return (
      <p className="app-main" role="status">
        {m.research_session_checking()}
      </p>
    )
  }
  if (session.status === 'signed_out') {
    return <ResearchLogin onSignedIn={signedIn} onBack={onBack} />
  }
  const section = researchSection(path, session.user.role)
  return (
    <div className="research-layout">
      <ResearchNav
        user={session.user}
        section={section}
        onNavigate={navigate}
        onSignOut={signOut}
        onStudyRan={() => setReportVersion((v) => v + 1)}
        onSignedOut={sessionEnded}
      />
      {section === 'accounts' && <ResearchAccounts currentEmail={session.user.email} onSignedOut={sessionEnded} />}
      {section === 'account' && <ResearchAccountPage role={session.user.role} onBack={onBack} />}
      {section === 'report' && (
        // A new key remounts the view, which reloads the report after a run.
        <ResearchAblationView key={reportVersion} onBack={onBack} onSignedOut={sessionEnded} />
      )}
    </div>
  )
}
