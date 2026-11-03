import { useEffect, useState } from 'react'
import { fetchResearchReport } from '../services/api'
import { SignedOutError } from '../services/researchAuth'
import type { ResearchReport } from '../types'

export type ResearchReportState =
  | { status: 'loading' }
  | { status: 'missing' }
  | { status: 'failed' }
  | { status: 'ready'; report: ResearchReport }

export function useResearchReport(onSignedOut: () => void): ResearchReportState {
  const [state, setState] = useState<ResearchReportState>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    fetchResearchReport(controller.signal)
      .then((report) => setState(report ? { status: 'ready', report } : { status: 'missing' }))
      .catch((err: Error) => {
        if (err instanceof SignedOutError) return onSignedOut()
        if (err.name !== 'AbortError') setState({ status: 'failed' })
      })
    return () => controller.abort()
  }, [onSignedOut])

  return state
}
