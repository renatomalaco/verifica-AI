import { channelLabel } from '../domain/verdict'
import type { ScanResponse } from '../types'

interface TechDetailsProps {
  response: ScanResponse
  onPrivacy?: () => void
}

export function TechDetails({ response, onPrivacy }: TechDetailsProps) {
  const { details } = response
  const signals = Object.entries(details.domain_signals ?? {})

  return (
    <details className="tech">
      <summary>Ver detalhes da investigação</summary>
      <dl>
        <dt>Tipo</dt>
        <dd>{channelLabel(details.channel)}</dd>
        <dt>Etapa que decidiu</dt>
        <dd>{details.deciding_stage}</dd>
        {details.category && (
          <>
            <dt>Categoria</dt>
            <dd>{details.category}</dd>
          </>
        )}
        {signals.map(([name, value]) => (
          <div key={name} className="contents">
            <dt>{name}</dt>
            <dd>{value}</dd>
          </div>
        ))}
        <dt>Código da análise</dt>
        <dd>{response.id}</dd>
      </dl>
      <p className="text-muted text-small tech__privacy">
        Esta análise foi registrada de forma anônima, sem o conteúdo e sem nada que identifique você, para medir o desempenho
        do Verifica na pesquisa.{' '}
        {onPrivacy && (
          <button type="button" className="link-button" onClick={onPrivacy}>
            Saiba como
          </button>
        )}
      </p>
    </details>
  )
}
