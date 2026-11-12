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

  it('explainScan asks for the explanation in the current locale', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ lines: ['a'], remaining_today: 2 }),
    })

    await explainScan('scan-1')

    const [url, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(url).toBe('/api/v1/scans/scan-1/explain')
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(JSON.parse(init.body)).toEqual({ locale: 'pt-BR' })
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
