import { render, screen, fireEvent } from '@testing-library/react'
import { afterEach, describe, it, expect, vi } from 'vitest'
import { ResearchAblationView } from './ResearchAblationView'
import { m } from '../paraglide/messages.js'
import type { ResearchReport } from '../types'

const REPORT: ResearchReport = {
  meta: {
    generated_at: '2026-10-27T18:00:00+00:00',
    seed: 42,
    split: { train: 21, test: 6 },
    triage: 'local classical classifier',
    disabled_stages: ['stage_2_inspection', 'visual_rag'],
    warnings: ['no feed snapshot loaded'],
  },
  modes: [
    {
      mode: 'cascade',
      status: 'executed',
      metrics: {
        accuracy: 0.9, precision: 0.8, recall: 0.75, f1_score: 0.7742, f2_score: 0.76,
        ece: 0.05, p95_latency_ms: 12.3, cost_per_1k_usd: 0, total_samples: 6,
      },
    },
    { mode: 'pure_vlm', status: 'not_executed', note: 'no LLM provider configured' },
  ],
  adversarial: { total: 2, detected_without_sanitization: 1, detected_with_sanitization: 2 },
  latex_table: '\\begin{table}...',
}

function mockFetch(status: number, body?: unknown) {
  global.fetch = vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => body })
}

describe('ResearchAblationView', () => {
  afterEach(() => vi.restoreAllMocks())

  it('shows the measured numbers of the latest study, never fixed ones', async () => {
    mockFetch(200, REPORT)
    render(<ResearchAblationView onBack={vi.fn()} />)

    expect(await screen.findByText(m.research_mode_cascade())).toBeInTheDocument()
    expect(screen.getByText('0.774')).toBeInTheDocument()
    expect(screen.getByText(m.research_not_executed({ note: 'no LLM provider configured' }))).toBeInTheDocument()
    expect(screen.getByText('no feed snapshot loaded')).toBeInTheDocument()
    expect(screen.getByText('\\begin{table}...')).toBeInTheDocument()
  })

  it('explains how to run the study when there is no report yet', async () => {
    mockFetch(404)
    render(<ResearchAblationView onBack={vi.fn()} />)
    expect(await screen.findByText(m.research_missing_title())).toBeInTheDocument()
  })

  it('calls onBack when the back button is clicked', async () => {
    mockFetch(404)
    const onBack = vi.fn()
    render(<ResearchAblationView onBack={onBack} />)
    fireEvent.click(screen.getByRole('button', { name: m.research_back() }))
    expect(onBack).toHaveBeenCalledTimes(1)
  })
})
