import { useState } from 'react'
import { metricCells } from '../domain/research'
import { useResearchReport } from '../hooks/useResearchReport'
import { m } from '../paraglide/messages.js'
import type { ResearchMode, ResearchModeName, ResearchReport } from '../types'
import { BackIcon } from './Icons'

interface Props {
  onBack: () => void
}

const MODE_LABELS: Record<ResearchModeName, () => string> = {
  heuristic: m.research_mode_heuristic,
  classical_nlp: m.research_mode_classic_nlp,
  pure_vlm: m.research_mode_vlm,
  cascade: m.research_mode_cascade,
}

const COLUMNS = [
  m.research_col_accuracy,
  m.research_col_precision,
  m.research_col_recall,
  m.research_col_f1,
  m.research_col_f2,
  m.research_col_ece,
  m.research_col_p95,
  m.research_col_cost,
]

// Shows the latest measured study. It never ships numbers of its own.
export function ResearchAblationView({ onBack }: Props) {
  const state = useResearchReport()

  return (
    <section className="app-main" aria-labelledby="pesquisa-titulo">
      <button type="button" className="btn btn-quiet align-start" onClick={onBack}>
        <BackIcon size={22} />
        {m.research_back()}
      </button>

      <header className="stack">
        <p className="text-small text-muted">{m.research_area()}</p>
        <h1 className="title-l" id="pesquisa-titulo">
          {m.research_title()}
        </h1>
        <p className="text-muted">{m.research_intro()}</p>
      </header>

      {state.status === 'loading' && <p role="status">{m.research_loading()}</p>}
      {state.status === 'failed' && <p role="alert">{m.research_failed()}</p>}
      {state.status === 'missing' && <MissingReport />}
      {state.status === 'ready' && <Report report={state.report} />}
    </section>
  )
}

function MissingReport() {
  return (
    <div className="research-notes stack">
      <h2 className="title-m">{m.research_missing_title()}</h2>
      <p className="text-muted">{m.research_missing_text()}</p>
    </div>
  )
}

function Report({ report }: { report: ResearchReport }) {
  return (
    <>
      <section className="stack" aria-labelledby="tabela-ablacao-titulo">
        <h2 className="title-m" id="tabela-ablacao-titulo">
          {m.research_table_title()}
        </h2>
        <div className="research-table-wrap">
          <table className="research-table">
            <thead>
              <tr>
                <th scope="col">{m.research_col_mode()}</th>
                {COLUMNS.map((column) => (
                  <th scope="col" key={column()}>
                    {column()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {report.modes.map((mode) => (
                <ModeRow key={mode.mode} mode={mode} />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {report.meta.warnings.length > 0 && <Warnings warnings={report.meta.warnings} />}
      <StudyNotes report={report} />
      <LatexExport latex={report.latex_table} />
    </>
  )
}

function ModeRow({ mode }: { mode: ResearchMode }) {
  const label = MODE_LABELS[mode.mode]()
  if (!mode.metrics) {
    return (
      <tr data-mode={mode.mode}>
        <th scope="row">{label}</th>
        <td colSpan={COLUMNS.length} data-skipped>
          {m.research_not_executed({ note: mode.note ?? '' })}
        </td>
      </tr>
    )
  }
  return (
    <tr data-mode={mode.mode}>
      <th scope="row">{label}</th>
      {metricCells(mode.metrics).map((cell, i) => (
        <td key={i}>{cell}</td>
      ))}
    </tr>
  )
}

function Warnings({ warnings }: { warnings: string[] }) {
  return (
    <section className="research-notes stack" aria-labelledby="avisos-titulo">
      <h2 className="title-m" id="avisos-titulo">
        {m.research_warnings_title()}
      </h2>
      <ul className="stack">
        {warnings.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </section>
  )
}

function StudyNotes({ report }: { report: ResearchReport }) {
  const { meta, adversarial } = report
  return (
    <section className="research-notes stack" aria-labelledby="metodo-titulo">
      <h2 className="title-m" id="metodo-titulo">
        {m.research_meta_title()}
      </h2>
      <p>{m.research_meta_generated({ date: new Date(meta.generated_at).toLocaleString(), seed: meta.seed })}</p>
      <p>{m.research_meta_split({ train: meta.split.train, test: meta.split.test })}</p>
      <p>{m.research_meta_triage({ triage: meta.triage })}</p>
      <p>{m.research_meta_disabled({ stages: meta.disabled_stages.join(', ') })}</p>
      <p>
        {m.research_adversarial({
          total: adversarial.total,
          raw: adversarial.detected_without_sanitization,
          clean: adversarial.detected_with_sanitization,
        })}
      </p>
    </section>
  )
}

function LatexExport({ latex }: { latex: string }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(latex)
      setCopied(true)
    } catch {
      // Clipboard can be blocked; the code stays visible to copy by hand.
    }
  }

  return (
    <section className="stack" aria-labelledby="latex-titulo">
      <div className="btn-row">
        <h2 className="title-m" id="latex-titulo">
          {m.research_latex_title()}
        </h2>
        <button type="button" className="btn btn-outline" onClick={copy}>
          {copied ? m.research_copied() : m.research_copy_latex()}
        </button>
      </div>
      <pre className="research-latex">{latex}</pre>
    </section>
  )
}
