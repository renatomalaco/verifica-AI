import { useEffect, useRef } from 'react'
import type { EvidenceData, StageEntry } from '../domain/investigation'
import { stageLabel } from '../domain/stages'
import { Evidence } from './Evidence'
import { CheckIcon } from './Icons'

const TITLES = {
  text: 'Investigando a mensagem…',
  url: 'Investigando o link…',
  image: 'Investigando o print…',
}

interface InvestigatingProps {
  evidence: EvidenceData
  stages: StageEntry[]
  onCancel: () => void
}

export function Investigating({ evidence, stages, onCancel }: InvestigatingProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  return (
    <section className="app-main" aria-labelledby="investigando-titulo" aria-busy="true">
      <Evidence evidence={evidence} mode="searching" />

      <div className="stack">
        <h1 className="title-l" id="investigando-titulo" ref={headingRef} tabIndex={-1}>
          {TITLES[evidence.tab]}
        </h1>
        <p className="text-muted">Procurando pistas de golpe. Leva alguns segundos.</p>
      </div>

      {stages.length > 0 && <StageList stages={stages} />}

      <div className="spacer" />
      <button type="button" className="btn btn-outline" onClick={onCancel}>
        Cancelar
      </button>
    </section>
  )
}

function StageList({ stages }: { stages: StageEntry[] }) {
  return (
    <ol className="stages" aria-label="Etapas da investigação">
      {stages.map((s) => (
        <li key={s.stage} className="stage" data-status={s.status}>
          <span className="stage__marker">
            <StageMarker status={s.status} />
          </span>
          <span>
            {stageLabel(s.stage)}
            <span className="sr-only">{s.status === 'done' ? ' (concluído)' : ' (em andamento)'}</span>
          </span>
        </li>
      ))}
    </ol>
  )
}

function StageMarker({ status }: { status: StageEntry['status'] }) {
  if (status === 'done') {
    return (
      <span className="stage__done">
        <CheckIcon size={15} />
      </span>
    )
  }
  if (status === 'started') return <span className="stage__active" />
  return null
}
