import { useState } from 'react'
import { runStudy } from '../services/api'
import { SignedOutError } from '../services/researchAuth'

export type StudyRun = 'idle' | 'running' | 'done' | 'failed'

// Admin action: runs the ablation study on the server, then the report is reloaded.
export function useStudyRun(onFinished: () => void, onSignedOut: () => void) {
  const [state, setState] = useState<StudyRun>('idle')

  const run = async () => {
    setState('running')
    try {
      await runStudy()
      setState('done')
      onFinished()
    } catch (err) {
      if (err instanceof SignedOutError) return onSignedOut()
      setState('failed')
    }
  }

  return { state, run }
}
