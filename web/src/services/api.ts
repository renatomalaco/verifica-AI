import type { ExplainResponse, ScanRequest, ScanResponse, StageEvent } from '../types'

const API_BASE = ''

export type ExplainErrorKind = 'unavailable' | 'quota' | 'failed'

export class ExplainError extends Error {
  kind: ExplainErrorKind
  retryAt: string | null

  constructor(kind: ExplainErrorKind, retryAt: string | null = null) {
    super(kind)
    this.name = 'ExplainError'
    this.kind = kind
    this.retryAt = retryAt
  }
}

// Detailed AI explanation, with a daily/monthly quota per device (R5b).
// Until the orchestrator has the endpoint, 404/501 become "unavailable".
export async function explainScan(scanId: string, signal?: AbortSignal): Promise<ExplainResponse> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}/api/v1/scans/${encodeURIComponent(scanId)}/explain`, {
      method: 'POST',
      credentials: 'same-origin',
      signal,
    })
  } catch (err) {
    if ((err as Error)?.name === 'AbortError') throw err
    throw new ExplainError('failed')
  }

  if (response.status === 429) {
    const body = await response.json().catch(() => ({}))
    throw new ExplainError('quota', typeof body?.retry_at === 'string' ? body.retry_at : null)
  }
  if (response.status === 404 || response.status === 405 || response.status === 501) {
    throw new ExplainError('unavailable')
  }
  if (!response.ok) {
    throw new ExplainError('failed')
  }
  const data = await response.json()
  if (!Array.isArray(data?.lines)) throw new ExplainError('failed')
  return data as ExplainResponse
}

export async function scanDirect(
  request: ScanRequest,
  signal?: AbortSignal
): Promise<ScanResponse> {
  const response = await fetch(`${API_BASE}/api/v1/scans`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Erro desconhecido')
    throw new Error(`Falha na verificação (${response.status}): ${errorText}`)
  }

  return response.json()
}

export async function scanStream(
  request: ScanRequest,
  onStage: (event: StageEvent) => void,
  onVerdict: (verdict: ScanResponse) => void,
  onError: (error: Error) => void,
  signal?: AbortSignal
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/api/v1/scans/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(request),
      signal,
    })

    if (!response.ok) {
      const err = await response.text().catch(() => 'Falha na resposta do servidor')
      throw new Error(`Erro na conexão com o scanner (${response.status}): ${err}`)
    }

    if (!response.body) {
      // Fallback to direct scan if ReadableStream is not available
      const direct = await scanDirect(request, signal)
      onVerdict(direct)
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const messages = buffer.split('\n\n')
      buffer = messages.pop() || ''

      for (const msg of messages) {
        if (!msg.trim()) continue

        let currentEvent = 'message'
        let currentData = ''

        const lines = msg.split('\n')
        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.replace('event:', '').trim()
          } else if (line.startsWith('data:')) {
            currentData = line.replace('data:', '').trim()
          }
        }

        if (!currentData) continue

        try {
          const parsed = JSON.parse(currentData)
          if (currentEvent === 'stage') {
            onStage(parsed as StageEvent)
          } else if (currentEvent === 'verdict') {
            onVerdict(parsed as ScanResponse)
          }
        } catch {
          // Ignore malformed keep-alive pulse data
        }
      }
    }
  } catch (err: any) {
    if (err.name === 'AbortError') {
      return
    }
    onError(err instanceof Error ? err : new Error(String(err)))
  }
}
