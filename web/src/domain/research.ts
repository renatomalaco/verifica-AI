// Formatting of the measured ablation metrics. No React, testable in isolation.
import type { ResearchMetrics } from '../types'

const fixed3 = (value: number): string => value.toFixed(3)

export function metricCells(m: ResearchMetrics): string[] {
  return [
    `${(m.accuracy * 100).toFixed(1)}%`,
    fixed3(m.precision),
    fixed3(m.recall),
    fixed3(m.f1_score),
    fixed3(m.f2_score),
    fixed3(m.ece),
    `${m.p95_latency_ms.toFixed(1)} ms`,
    `$${m.cost_per_1k_usd.toFixed(3)}`,
  ]
}
