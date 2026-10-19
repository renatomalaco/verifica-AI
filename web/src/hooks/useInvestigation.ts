import { useEffect, useRef, useState } from 'react'
import { friendlyErrorMessage, toScanRequest, upsertStage, type EvidenceData, type StageEntry } from '../domain/investigation'
import { scanStream } from '../services/api'
import type { ScanResponse } from '../types'

export type Investigation =
  | { status: 'idle' }
  | { status: 'scanning'; evidence: EvidenceData; stages: StageEntry[] }
  | { status: 'result'; evidence: EvidenceData; verdict: ScanResponse }
  | { status: 'error'; evidence: EvidenceData; message: string }

// Screen use case: investigate evidence while following the SSE stages.
export function useInvestigation() {
  const [state, setState] = useState<Investigation>({ status: 'idle' })
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => () => abortRef.current?.abort(), [])

  const start = async (evidence: EvidenceData) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setState({ status: 'scanning', evidence, stages: [] })

    const stillCurrent = () => !controller.signal.aborted
    await scanStream(
      toScanRequest(evidence),
      (event) =>
        setState((s) => (s.status === 'scanning' && stillCurrent() ? { ...s, stages: upsertStage(s.stages, event) } : s)),
      (verdict) => stillCurrent() && setState({ status: 'result', evidence, verdict }),
      (error) => stillCurrent() && setState({ status: 'error', evidence, message: friendlyErrorMessage(error, navigator.onLine) }),
      controller.signal
    )
  }

  const reset = () => {
    abortRef.current?.abort()
    setState({ status: 'idle' })
  }

  return { state, start, reset }
}
