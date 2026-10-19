import { channelLabel } from '../domain/verdict'
import type { ScanResponse } from '../types'
import { m } from '../paraglide/messages.js'

interface TechDetailsProps {
  response: ScanResponse
  onPrivacy?: () => void
}

export function TechDetails({ response, onPrivacy }: TechDetailsProps) {
  const { details } = response
  const signals = Object.entries(details.domain_signals ?? {})

  return (
    <details className="tech">
      <summary>{m.verdict_tech_summary()}</summary>
      <dl>
        <dt>{m.verdict_tech_type()}</dt>
        <dd>{channelLabel(details.channel)}</dd>
        <dt>{m.verdict_tech_deciding_stage()}</dt>
        <dd>{details.deciding_stage}</dd>
        {details.category && (
          <>
            <dt>{m.verdict_tech_category()}</dt>
            <dd>{details.category}</dd>
          </>
        )}
        {signals.map(([name, value]) => (
          <div key={name} className="contents">
            <dt>{name}</dt>
            <dd>{value}</dd>
          </div>
        ))}
        <dt>{m.verdict_tech_scan_id()}</dt>
        <dd>{response.id}</dd>
      </dl>
      <p className="text-muted text-small tech__privacy">
        {m.verdict_tech_privacy()}{' '}
        {onPrivacy && (
          <button type="button" className="link-button" onClick={onPrivacy}>
            {m.verdict_tech_privacy_link()}
          </button>
        )}
      </p>
    </details>
  )
}
