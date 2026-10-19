import { remainingExplanationsText } from '../domain/verdict'
import type { Explanation } from '../hooks/useExplanation'
import type { ExplainError } from '../services/api'
import { m } from '../paraglide/messages.js'
import { getLocale } from '../paraglide/runtime.js'

export function ExplanationSheet({ explanation }: { explanation: Explanation }) {
  if (explanation.status === 'closed') return null

  return (
    <section className="sheet" aria-label={m.verdict_explanation_label()} aria-live="polite">
      {explanation.status === 'loading' && <Writing />}
      {explanation.status === 'ready' && <ExplanationLines lines={explanation.lines} remaining={explanation.remaining} />}
      {explanation.status === 'error' && <ExplanationError kind={explanation.kind} retryAt={explanation.retryAt} />}
    </section>
  )
}

function Writing() {
  return (
    <p className="text-muted inline-status">
      {m.verdict_explanation_writing()}
      <span className="dots" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
    </p>
  )
}

function ExplanationLines({ lines, remaining }: { lines: string[]; remaining?: number }) {
  return (
    <>
      <h2 className="title-m">{m.verdict_explanation_heading()}</h2>
      {lines.map((line, i) => (
        <p key={i} className="explain-line" style={{ animationDelay: `${0.05 + i * 0.15}s` }}>
          {line}
        </p>
      ))}
      {typeof remaining === 'number' && (
        <>
          <div className="divider" />
          <p className="text-muted text-small">{remainingExplanationsText(remaining)}</p>
        </>
      )}
    </>
  )
}

function ExplanationError({ kind, retryAt }: { kind: ExplainError['kind']; retryAt: string | null }) {
  if (kind === 'quota') {
    return <p>{m.verdict_explanation_quota({ returns: quotaReturnText(retryAt) })}</p>
  }
  if (kind === 'unavailable') {
    return <p>{m.verdict_explanation_unavailable()}</p>
  }
  return <p>{m.verdict_explanation_failed()}</p>
}

function quotaReturnText(retryAt: string | null): string {
  const when = retryAt ? new Date(retryAt) : null
  if (!when || Number.isNaN(when.getTime())) return m.verdict_explanation_returns_tomorrow()
  return m.verdict_explanation_returns_at({ when: when.toLocaleString(getLocale(), { weekday: 'long', hour: '2-digit', minute: '2-digit' }) })
}
