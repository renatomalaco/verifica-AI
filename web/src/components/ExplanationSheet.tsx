import { remainingExplanationsText } from '../domain/verdict'
import type { Explanation } from '../hooks/useExplanation'
import type { ExplainError } from '../services/api'

export function ExplanationSheet({ explanation }: { explanation: Explanation }) {
  if (explanation.status === 'closed') return null

  return (
    <section className="sheet" aria-label="Explicação" aria-live="polite">
      {explanation.status === 'loading' && <Writing />}
      {explanation.status === 'ready' && <ExplanationLines lines={explanation.lines} remaining={explanation.remaining} />}
      {explanation.status === 'error' && <ExplanationError kind={explanation.kind} retryAt={explanation.retryAt} />}
    </section>
  )
}

function Writing() {
  return (
    <p className="text-muted inline-status">
      Escrevendo para você
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
      <h2 className="title-m">Por que o Verifica chegou a essa resposta</h2>
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
    return (
      <p>
        Você já usou as explicações de hoje. {quotaReturnText(retryAt)} O resultado e o que fazer continuam aqui em cima.
      </p>
    )
  }
  if (kind === 'unavailable') {
    return <p>A explicação detalhada ainda não está disponível. O resultado e o que fazer continuam valendo.</p>
  }
  return <p>A explicação não pôde ser escrita agora. Tente de novo em instantes.</p>
}

function quotaReturnText(retryAt: string | null): string {
  const when = retryAt ? new Date(retryAt) : null
  if (!when || Number.isNaN(when.getTime())) return 'Elas voltam amanhã.'
  return `Elas voltam ${when.toLocaleString('pt-BR', { weekday: 'long', hour: '2-digit', minute: '2-digit' })}.`
}
