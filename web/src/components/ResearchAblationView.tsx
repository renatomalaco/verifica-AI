import React, { useState } from 'react'
import { ArrowLeft, Copy, Check, FlaskConical, Code2, BookOpen } from 'lucide-react'
import { m } from '../paraglide/messages.js'

interface Props {
  onBack: () => void
}

interface AblationRow {
  name: () => string
  highlight?: boolean
  acc: string
  prec: string
  rec: string
  f1: string
  f2: string
  ece: string
  p95: string
  cost: string
}

const DEFAULT_ROWS: AblationRow[] = [
  {
    name: m.research_mode_heuristic,
    acc: '52.4%',
    prec: '1.000',
    rec: '0.286',
    f1: '0.444',
    f2: '0.333',
    ece: '0.380',
    p95: '6.0 ms',
    cost: '$0.000',
  },
  {
    name: m.research_mode_classic_nlp,
    acc: '81.0%',
    prec: '0.846',
    rec: '0.786',
    f1: '0.815',
    f2: '0.797',
    ece: '0.124',
    p95: '8.5 ms',
    cost: '$0.001',
  },
  {
    name: m.research_mode_vlm,
    acc: '90.5%',
    prec: '0.929',
    rec: '0.929',
    f1: '0.929',
    f2: '0.929',
    ece: '0.045',
    p95: '1150.0 ms',
    cost: '$1.500',
  },
  {
    name: m.research_mode_cascade,
    highlight: true,
    acc: '95.2%',
    prec: '0.933',
    rec: '1.000',
    f1: '0.966',
    f2: '0.986',
    ece: '0.038',
    p95: '45.0 ms',
    cost: '$0.150',
  },
]

// Verbatim LaTeX for the thesis document, which is written in Portuguese.
const LATEX_SNIPPET = `\\begin{table}[htbp]
\\centering
\\caption{Resultados do Estudo de Ablação e Comparativo de Eficácia da Plataforma Verifica AI}
\\label{tab:ablation_results}
\\begin{tabular}{lcccccccc}
\\toprule
\\textbf{Modo} & \\textbf{Acc.} & \\textbf{Prec.} & \\textbf{Rec.} & \\textbf{F1} & \\textbf{F2} & \\textbf{ECE} & \\textbf{P95 (ms)} & \\textbf{Custo/1k (USD)} \\\\
\\midrule
Modo 1 (Heur\\'istico / Sinais de Dom\\'inio) & 52.4\\% & 1.000 & 0.286 & 0.444 & 0.333 & 0.380 & 6.0 & \\$0.000 \\\\
Modo 1b (NLP Cl\\'assico TF-IDF+LR) & 81.0\\% & 0.846 & 0.786 & 0.815 & 0.797 & 0.124 & 8.5 & \\$0.001 \\\\
Modo 2 (VLM Puro Multimodal) & 90.5\\% & 0.929 & 0.929 & 0.929 & 0.929 & 0.045 & 1150.0 & \\$1.500 \\\\
\\textbf{Modo 3 (Cascata Verifica AI)} & \\textbf{95.2\\%} & \\textbf{0.933} & \\textbf{1.000} & \\textbf{0.966} & \\textbf{0.986} & \\textbf{0.038} & \\textbf{45.0} & \\textbf{\\$0.150} \\\\
\\bottomrule
\\end{tabular}
\\end{table}`

export const ResearchAblationView: React.FC<Props> = ({ onBack }) => {
  const [copied, setCopied] = useState(false)

  const handleCopyLatex = async () => {
    try {
      await navigator.clipboard.writeText(LATEX_SNIPPET)
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    } catch {
      // Fail silently on clipboard errors
    }
  }

  return (
    <div className="input-card" style={{ maxWidth: '1000px', margin: '0 auto', gap: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <button
          type="button"
          onClick={onBack}
          className="btn-primary"
          style={{ width: 'auto', minWidth: '180px', height: '44px', padding: '0 1rem' }}
          aria-label={m.research_back()}
        >
          <ArrowLeft size={18} aria-hidden="true" />
          <span>{m.research_back()}</span>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#60a5fa' }}>
          <FlaskConical size={24} aria-hidden="true" />
          <span style={{ fontWeight: 600, fontSize: '1.1rem' }}>{m.research_area()}</span>
        </div>
      </div>

      <header>
        <h1 style={{ fontSize: '1.8rem', color: 'var(--color-text-primary)' }}>
          {m.research_title()}
        </h1>
        <p style={{ fontSize: '1.1rem', color: 'var(--color-text-secondary)', marginTop: '0.5rem' }}>
          {m.research_intro()}
        </p>
      </header>

      {/* Results table */}
      <section aria-labelledby="tabela-ablation-titulo" style={{ overflowX: 'auto' }}>
        <h2 id="tabela-ablation-titulo" style={{ fontSize: '1.3rem', color: 'var(--color-text-primary)', marginBottom: '0.75rem' }}>
          {m.research_table_title()}
        </h2>

        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', minWidth: '650px' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid rgba(255, 255, 255, 0.15)', color: 'var(--color-text-muted)' }}>
              <th style={{ padding: '0.75rem 0.5rem' }}>{m.research_col_mode()}</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>{m.research_col_accuracy()}</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>{m.research_col_precision()}</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>{m.research_col_recall()}</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>{m.research_col_f1()}</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>{m.research_col_f2()}</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>{m.research_col_ece()}</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>{m.research_col_p95()}</th>
              <th style={{ padding: '0.75rem 0.5rem' }}>{m.research_col_cost()}</th>
            </tr>
          </thead>
          <tbody>
            {DEFAULT_ROWS.map((row, idx) => {
              const isHighlight = row.highlight === true
              return (
                <tr
                  key={idx}
                  style={{
                    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                    backgroundColor: isHighlight ? 'rgba(37, 99, 235, 0.15)' : 'transparent',
                    fontWeight: isHighlight ? 600 : 400,
                  }}
                >
                  <td style={{ padding: '0.75rem 0.5rem' }}>{row.name()}</td>
                  <td style={{ padding: '0.75rem 0.5rem' }}>{row.acc}</td>
                  <td style={{ padding: '0.75rem 0.5rem' }}>{row.prec}</td>
                  <td style={{ padding: '0.75rem 0.5rem' }}>{row.rec}</td>
                  <td style={{ padding: '0.75rem 0.5rem', color: isHighlight ? '#4ade80' : 'inherit' }}>{row.f1}</td>
                  <td style={{ padding: '0.75rem 0.5rem' }}>{row.f2}</td>
                  <td style={{ padding: '0.75rem 0.5rem' }}>{row.ece}</td>
                  <td style={{ padding: '0.75rem 0.5rem' }}>{row.p95}</td>
                  <td style={{ padding: '0.75rem 0.5rem' }}>{row.cost}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </section>

      {/* LaTeX section for the thesis */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ fontSize: '1.25rem', color: 'var(--color-text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Code2 size={20} color="#60a5fa" aria-hidden="true" />
            <span>{m.research_latex_title()}</span>
          </h2>
          <button
            type="button"
            onClick={handleCopyLatex}
            className="btn-primary"
            style={{ width: 'auto', minWidth: '190px', height: '40px', padding: '0 0.75rem', fontSize: '0.95rem' }}
            aria-label={m.research_copy_latex()}
          >
            {copied ? <Check size={16} aria-hidden="true" /> : <Copy size={16} aria-hidden="true" />}
            <span>{copied ? m.research_copied() : m.research_copy_latex()}</span>
          </button>
        </div>

        <pre
          style={{
            backgroundColor: '#070d1e',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '8px',
            padding: '1rem',
            overflowX: 'auto',
            fontSize: '0.9rem',
            color: '#93c5fd',
            fontFamily: 'monospace',
          }}
        >
          {LATEX_SNIPPET}
        </pre>
      </section>

      {/* Academic summary */}
      <section style={{ backgroundColor: 'rgba(255, 255, 255, 0.03)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <h3 style={{ fontSize: '1.15rem', color: 'var(--color-text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <BookOpen size={18} color="#38bdf8" aria-hidden="true" />
          <span>{m.research_conclusions_title()}</span>
        </h3>
        <ul style={{ paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', color: 'var(--color-text-secondary)', fontSize: '1.05rem' }}>
          <li>
            <strong>{m.research_conclusion_cascade_label()}</strong> {m.research_conclusion_cascade_text()}
          </li>
          <li>
            <strong>{m.research_conclusion_cost_label()}</strong> {m.research_conclusion_cost_text()}
          </li>
          <li>
            <strong>{m.research_conclusion_calibration_label()}</strong> {m.research_conclusion_calibration_text()}
          </li>
        </ul>
      </section>
    </div>
  )
}
