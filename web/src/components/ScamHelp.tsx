import { useState } from 'react'
import { ChevronIcon } from './Icons'
import { m } from '../paraglide/messages.js'

export function ScamHelp() {
  const [open, setOpen] = useState(false)

  return (
    <div className="stack stack-actions reveal-2">
      <button
        type="button"
        className="btn btn-ghost btn-disclosure"
        aria-expanded={open}
        aria-controls="ja-cai"
        onClick={() => setOpen((o) => !o)}
      >
        <span>{m.verdict_scam_help_toggle()}</span>
        <ChevronIcon size={20} className="chevron" />
      </button>
      {open && (
        <div className="sheet" id="ja-cai">
          <p>
            <strong>{m.verdict_scam_help_bank_strong()}</strong> {m.verdict_scam_help_bank_rest()}
          </p>
          <p>
            <strong>{m.verdict_scam_help_pix_strong()}</strong> {m.verdict_scam_help_pix_rest()}
          </p>
          <p>
            <strong>{m.verdict_scam_help_report_strong()}</strong> {m.verdict_scam_help_report_rest()}
          </p>
          <p className="text-muted text-small">{m.verdict_scam_help_not_your_fault()}</p>
        </div>
      )}
    </div>
  )
}
