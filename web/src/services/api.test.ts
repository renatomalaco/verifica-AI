import { describe, it, expect, vi, beforeEach } from 'vitest'
import { explainScan, fetchResearchReport, runStudy, scanDirect, scanStream } from './api'
import { ScanRateLimitedError } from '../domain/investigation'
import type { ScanResponse, StageEvent } from '../types'

describe('API Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('scanDirect successfully posts and parses ScanResponse', async () => {
    const mockResponse: ScanResponse = {
      id: '123e4567-e89b-12d3-a456-426614174000',
      threat_level: 'GOLPE',
      verdict_message: 'scam_financial_threat',
      details: {
        channel: 'texto',
        deciding_stage: 'triage',
        scores: { triage_phishing: 0.95 },
      },
    }

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    })

    const result = await scanDirect({ content: 'Urgente: atualize sua conta bb' })
    expect(result.threat_level).toBe('GOLPE')
    expect(result.verdict_message).toBe('scam_financial_threat')
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/scans',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
    )
  })

  it('scanDirect throws on server error', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => 'Internal Server Error',
    })

    await expect(scanDirect({ content: 'teste' })).rejects.toThrow('Scan failed')
  })

  it('scanDirect turns the flood guard 429 into a rate-limit error with the retry time', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(rateLimitedResponse())

    const error = await scanDirect({ content: 'teste' }).catch((e) => e)
    expect(error).toBeInstanceOf(ScanRateLimitedError)
    expect(error.retryAt).toBe('2026-11-10T17:32:00Z')
  })

  it('scanStream reports the flood guard 429 as a rate-limit error', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(rateLimitedResponse())
    const onError = vi.fn()

    await scanStream({ content: 'teste' }, vi.fn(), vi.fn(), onError)

    const error = onError.mock.calls[0][0]
    expect(error).toBeInstanceOf(ScanRateLimitedError)
    expect(error.retryAt).toBe('2026-11-10T17:32:00Z')
  })

  it('scanStream treats any other 429 as a generic failure', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 429, json: async () => ({}), text: async () => '' })
    const onError = vi.fn()

    await scanStream({ content: 'teste' }, vi.fn(), vi.fn(), onError)

    expect(onError.mock.calls[0][0]).not.toBeInstanceOf(ScanRateLimitedError)
  })

  it('scanStream processes SSE stage events and verdict event', async () => {
    const ssePayload = [
      'event: stage\n',
      'data: {"stage":"triage","status":"started"}\n\n',
      'event: stage\n',
      'data: {"stage":"triage","status":"done"}\n\n',
      'event: verdict\n',
      'data: {"id":"123","threat_level":"SEGURO","verdict_message":"safe","details":{"channel":"texto","deciding_stage":"triage","scores":{}}}\n\n',
    ].join('')

    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(ssePayload))
        controller.close()
      },
    })

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      body: stream,
    })

    const stages: StageEvent[] = []
    let verdict: ScanResponse | null = null

    await scanStream(
      { content: 'Olá tudo bem?' },
      (stage) => stages.push(stage),
      (v) => {
        verdict = v
      },
      (err) => {
        throw err
      }
    )

    expect(stages).toHaveLength(2)
    expect(stages[0]).toEqual({ stage: 'triage', status: 'started' })
    expect(stages[1]).toEqual({ stage: 'triage', status: 'done' })
    expect(verdict).not.toBeNull()
    expect((verdict as any)?.threat_level).toBe('SEGURO')
  })

  // sse-starlette (the orchestrator) ends every line with \r\n; the SSE spec allows \r\n, \n and \r.
  const VERDICT_JSON =
    '{"id":"1","threat_level":"SEGURO","verdict_message":"safe_own_address","details":{"channel":"url","deciding_stage":"stage_0_own_address","scores":{}}}'

  function streamOf(...chunks: string[]) {
    const encoder = new TextEncoder()
    const body = new ReadableStream({
      start(controller) {
        for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
        controller.close()
      },
    })
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, body })
  }

  async function collect() {
    const stages: StageEvent[] = []
    const verdicts: ScanResponse[] = []
    const errors: Error[] = []
    await scanStream({ content: 'https://verifica-ai.duckdns.org' }, (s) => stages.push(s), (v) => verdicts.push(v), (e) => errors.push(e))
    return { stages, verdicts, errors }
  }

  it('scanStream reads events separated by \\r\\n, as the orchestrator sends them', async () => {
    streamOf(
      'event: stage\r\ndata: {"stage":"stage_0_cache","status":"done"}\r\n\r\n',
      `event: verdict\r\ndata: ${VERDICT_JSON}\r\n\r\n`,
    )

    const { stages, verdicts, errors } = await collect()

    expect(stages).toEqual([{ stage: 'stage_0_cache', status: 'done' }])
    expect(verdicts.map((v) => v.verdict_message)).toEqual(['safe_own_address'])
    expect(errors).toEqual([])
  })

  it('scanStream joins an event split across network chunks, even between \\r and \\n', async () => {
    const event = `event: verdict\r\ndata: ${VERDICT_JSON}\r\n\r\n`
    const cut = event.indexOf('\r\n\r\n') + 1

    streamOf(event.slice(0, cut), event.slice(cut))

    expect((await collect()).verdicts).toHaveLength(1)
  })

  it('scanStream reads a last event that arrives without the closing blank line', async () => {
    streamOf(`event: verdict\ndata: ${VERDICT_JSON}`)

    expect((await collect()).verdicts).toHaveLength(1)
  })

  it('scanStream reports an error when the stream ends without a verdict, instead of waiting forever', async () => {
    streamOf('event: stage\r\ndata: {"stage":"stage_0_cache","status":"started"}\r\n\r\n')

    const { verdicts, errors } = await collect()

    expect(verdicts).toEqual([])
    expect(errors).toHaveLength(1)
  })

  it('explainScan asks for the explanation in the current locale', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ lines: ['a'], remaining_today: 2 }),
    })

    await explainScan('scan-1')

    const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls
    const [url, init] = calls[calls.length - 1]
    expect(url).toBe('/api/v1/scans/scan-1/explain')
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(JSON.parse(init.body)).toEqual({ locale: 'pt-BR' })
  })

  it('explainScan renews a research session first, so an unlimited account is recognized', async () => {
    const answers: Record<string, number> = { '/api/v1/auth/me': 401, '/api/v1/auth/refresh': 200 }
    globalThis.fetch = vi.fn(async (url: string) => {
      const status = answers[url] ?? 200
      if (url === '/api/v1/auth/refresh') answers['/api/v1/auth/me'] = 200
      return { ok: status < 400, status, json: async () => ({ lines: ['a'], remaining_today: null }) }
    }) as unknown as typeof fetch

    await explainScan('scan-1')

    const urls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.map(([url]) => url)
    expect(urls).toContain('/api/v1/auth/refresh')
    expect(urls.indexOf('/api/v1/auth/refresh')).toBeLessThan(urls.indexOf('/api/v1/scans/scan-1/explain'))
  })

  it('explainScan still works for a visitor without any session', async () => {
    globalThis.fetch = vi.fn(async (url: string) => {
      const status = url.startsWith('/api/v1/auth') ? 401 : 200
      return { ok: status < 400, status, json: async () => ({ lines: ['a'], remaining_today: 2 }) }
    }) as unknown as typeof fetch

    await expect(explainScan('scan-1')).resolves.toEqual({ lines: ['a'], remaining_today: 2 })
  })

  it('fetchResearchReport returns null while no study has been run', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({}) })
    await expect(fetchResearchReport()).resolves.toBeNull()
  })

  it('fetchResearchReport returns the latest report', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ modes: [] }) })
    await expect(fetchResearchReport()).resolves.toEqual({ modes: [] })
    expect(globalThis.fetch).toHaveBeenCalledWith('/pesquisa/report', expect.anything())
  })

  it('runStudy asks the research-runner to run a new study', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ modes: [] }) })
    await runStudy()
    expect(globalThis.fetch).toHaveBeenCalledWith('/pesquisa/run', expect.objectContaining({ method: 'POST' }))
  })

  it('runStudy reports a failure', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({}) })
    await expect(runStudy()).rejects.toThrow()
  })
})

function rateLimitedResponse() {
  const body = { code: 'scan_rate_limited', retry_at: '2026-11-10T17:32:00Z' }
  return { ok: false, status: 429, json: async () => body, text: async () => JSON.stringify(body) }
}
