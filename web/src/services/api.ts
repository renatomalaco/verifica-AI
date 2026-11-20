import { getLocale } from '../paraglide/runtime.js'
import { ScanRateLimitedError } from '../domain/investigation'
import { researchFetch } from './researchAuth'
import type { ExplainResponse, ResearchReport, ScanRequest, ScanResponse, StageEvent } from '../types'

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
      headers: { 'Content-Type': 'application/json' },
      // The explanation is written by the LLM, so it has to know the person's language.
      body: JSON.stringify({ locale: getLocale() }),
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

  if (!response.ok) await throwScanFailure(response, 'Scan failed')

  return response.json()
}

// The flood guard answers 429 with a code; anything else stays a generic failure.
async function throwScanFailure(response: Response, label: string): Promise<never> {
  if (response.status === 429) {
    const body = await response.json().catch(() => ({}))
    if (body?.code === 'scan_rate_limited') {
      throw new ScanRateLimitedError(typeof body.retry_at === 'string' ? body.retry_at : null)
    }
  }
  const detail = await response.text().catch(() => '')
  throw new Error(`${label} (${response.status}): ${detail}`)
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

    if (!response.ok) await throwScanFailure(response, 'Scanner connection error')

    if (!response.body) {
      // Fallback to direct scan if ReadableStream is not available
      const direct = await scanDirect(request, signal)
      onVerdict(direct)
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    const dispatch = (block: string): boolean => dispatchEvent(block, onStage, onVerdict)
    let buffer = ''
    let gotVerdict = false

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      const { events, rest } = takeEvents(buffer + decoder.decode(value, { stream: true }))
      buffer = rest
      for (const block of events) gotVerdict = dispatch(block) || gotVerdict
    }
    // The last event may come without its closing blank line.
    for (const block of takeEvents(buffer + '\n\n').events) gotVerdict = dispatch(block) || gotVerdict

    // A stream that ends without a verdict must not leave the screen investigating forever.
    if (!gotVerdict) onError(new Error('Scan stream ended without a verdict'))
  } catch (err: any) {
    if (err.name === 'AbortError') {
      return
    }
    onError(err instanceof Error ? err : new Error(String(err)))
  }
}

// Latest ablation study; null until the admin runs one. Needs a signed-in researcher (R5a).
export async function fetchResearchReport(signal?: AbortSignal): Promise<ResearchReport | null> {
  const response = await researchFetch(`${API_BASE}/pesquisa/report`, { signal })
  if (response.status === 404) return null
  if (!response.ok) throw new Error(`Research report failed (${response.status})`)
  return response.json()
}

// Admin only: runs the whole ablation study on the server (heavy, and paid when Gemini is on).
export async function runStudy(): Promise<void> {
  const response = await researchFetch(`${API_BASE}/pesquisa/run`, { method: 'POST' })
  if (!response.ok) throw new Error(`Research run failed (${response.status})`)
}

// SSE accepts \r\n, \n and \r as line endings; sse-starlette (the orchestrator) sends \r\n.
// A trailing \r is kept for the next chunk, since it may be the first half of a \r\n.
function takeEvents(buffer: string): { events: string[]; rest: string } {
  const pendingCr = buffer.endsWith('\r')
  const text = (pendingCr ? buffer.slice(0, -1) : buffer).replace(/\r\n?/g, '\n')
  const blocks = text.split('\n\n')
  const rest = (blocks.pop() ?? '') + (pendingCr ? '\r' : '')
  return { events: blocks.filter((block) => block.trim()), rest }
}

// Returns true when the block was the verdict.
function dispatchEvent(
  block: string,
  onStage: (event: StageEvent) => void,
  onVerdict: (verdict: ScanResponse) => void,
): boolean {
  let event = 'message'
  const data: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice('event:'.length).trim()
    if (line.startsWith('data:')) data.push(line.slice('data:'.length).replace(/^ /, ''))
  }
  if (!data.length) return false
  try {
    const parsed = JSON.parse(data.join('\n'))
    if (event === 'stage') onStage(parsed as StageEvent)
    if (event === 'verdict') onVerdict(parsed as ScanResponse)
    return event === 'verdict'
  } catch {
    return false // keep-alive pings carry no JSON
  }
}
