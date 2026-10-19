import { useEffect, useRef } from 'react'
import { m } from '../paraglide/messages.js'
import type { EvidenceData, StageEntry } from '../domain/investigation'
import { stageLabel } from '../domain/stages'
import { Evidence } from './Evidence'
import { CheckIcon } from './Icons'
import type { InputTab } from '../types'

const TITLES: Record<InputTab, () => string> = {
  text: m.home_investigating_text,
  url: m.home_investigating_url,
  image: m.home_investigating_image,
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
          {TITLES[evidence.tab]()}
        </h1>
        <p className="text-muted">{m.home_investigating_hint()}</p>
      </div>

      {stages.length > 0 && <StageList stages={stages} />}

      <div className="spacer" />
      <button type="button" className="btn btn-outline" onClick={onCancel}>
        {m.home_cancel()}
      </button>
    </section>
  )
}

function StageList({ stages }: { stages: StageEntry[] }) {
  return (
    <ol className="stages" aria-label={m.home_stages_label()}>
      {stages.map((s) => (
        <li key={s.stage} className="stage" data-status={s.status}>
          <span className="stage__marker">
            <StageMarker status={s.status} />
          </span>
          <span>
            {stageLabel(s.stage)}
            <span className="sr-only"> {s.status === 'done' ? m.home_stage_status_done() : m.home_stage_status_started()}</span>
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
