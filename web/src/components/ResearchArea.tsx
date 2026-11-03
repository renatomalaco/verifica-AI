import { useState } from 'react'
import { useResearchSession } from '../hooks/useResearchSession'
import { m } from '../paraglide/messages.js'
import { ResearchAblationView } from './ResearchAblationView'
import { ResearchLogin } from './ResearchLogin'
import { ResearchNav } from './ResearchNav'

interface Props {
  onBack: () => void
}

// Gate of the research area (R5a): nothing of the study shows up without a signed-in account.
export function ResearchArea({ onBack }: Props) {
  const { session, signedIn, signOut, sessionEnded } = useResearchSession()
  const [reportVersion, setReportVersion] = useState(0)

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
  return (
    <div className="research-layout">
      <ResearchNav
        user={session.user}
        onSignOut={signOut}
        onStudyRan={() => setReportVersion((v) => v + 1)}
        onSignedOut={sessionEnded}
      />
      {/* A new key remounts the view, which reloads the report after a run. */}
      <ResearchAblationView key={reportVersion} onBack={onBack} onSignedOut={sessionEnded} />
    </div>
  )
}
