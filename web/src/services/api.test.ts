import { describe, it, expect, vi, beforeEach } from 'vitest'
import { scanDirect, scanStream } from './api'
import type { ScanResponse, StageEvent } from '../types'

describe('API Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('scanDirect successfully posts and parses ScanResponse', async () => {
    const mockResponse: ScanResponse = {
      id: '123e4567-e89b-12d3-a456-426614174000',
      threat_level: 'GOLPE',
      verdict_plain: 'Mensagem falsa simulando banco.',
      action_advice: 'Não clique no link.',
      details: {
        channel: 'texto',
        deciding_stage: 'triage',
        scores: { triage_phishing: 0.95 },
      },
    }

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    })

    const result = await scanDirect({ content: 'Urgente: atualize sua conta bb' })
    expect(result.threat_level).toBe('GOLPE')
    expect(result.verdict_plain).toContain('Mensagem falsa')
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/scans',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
    )
  })

  it('scanDirect throws on server error', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => 'Internal Server Error',
    })

    await expect(scanDirect({ content: 'teste' })).rejects.toThrow('Falha na verificação')
  })

  it('scanStream processes SSE stage events and verdict event', async () => {
    const ssePayload = [
      'event: stage\n',
      'data: {"stage":"triage","status":"started"}\n\n',
      'event: stage\n',
      'data: {"stage":"triage","status":"done"}\n\n',
      'event: verdict\n',
      'data: {"id":"123","threat_level":"SEGURO","verdict_plain":"Tudo certo","action_advice":"Pode prosseguir","details":{"channel":"texto","deciding_stage":"triage","scores":{}}}\n\n',
    ].join('')

    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(ssePayload))
        controller.close()
      },
    })

    global.fetch = vi.fn().mockResolvedValue({
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
})
