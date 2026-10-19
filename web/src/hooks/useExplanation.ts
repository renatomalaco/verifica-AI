import { useEffect, useRef, useState } from 'react'
import { ExplainError, explainScan } from '../services/api'

export type Explanation =
  | { status: 'closed' }
  | { status: 'loading' }
  | { status: 'ready'; lines: string[]; remaining?: number }
  | { status: 'error'; kind: ExplainError['kind']; retryAt: string | null }

// Explain button: opening fetches the explanation; closing cancels the pending request.
export function useExplanation(scanId: string) {
  const [explanation, setExplanation] = useState<Explanation>({ status: 'closed' })
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => () => abortRef.current?.abort(), [])

  const close = () => {
    abortRef.current?.abort()
    setExplanation({ status: 'closed' })
  }

  const open = async () => {
    const controller = new AbortController()
    abortRef.current = controller
    setExplanation({ status: 'loading' })
    try {
      const data = await explainScan(scanId, controller.signal)
      setExplanation({ status: 'ready', lines: data.lines, remaining: data.remaining_today })
    } catch (err) {
      if ((err as Error)?.name === 'AbortError') return
      const e = err instanceof ExplainError ? err : new ExplainError('failed')
      setExplanation({ status: 'error', kind: e.kind, retryAt: e.retryAt })
    }
  }

  const toggle = () => (explanation.status === 'closed' ? open() : close())

  return { explanation, toggle }
}
