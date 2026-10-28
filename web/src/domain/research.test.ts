import { describe, expect, it } from 'vitest'
import { metricCells } from './research'

describe('metricCells', () => {
  it('formats the measured metrics in table order', () => {
    const cells = metricCells({
      accuracy: 0.9,
      precision: 0.8,
      recall: 0.75,
      f1_score: 0.7742,
      f2_score: 0.76,
      ece: 0.05,
      p95_latency_ms: 12.34,
      cost_per_1k_usd: 0,
      total_samples: 10,
    })
    expect(cells).toEqual(['90.0%', '0.800', '0.750', '0.774', '0.760', '0.050', '12.3 ms', '$0.000'])
  })
})
