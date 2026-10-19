import type { EvidenceData } from '../domain/investigation'
import type { InputTab, ThreatLevel } from '../types'
import { Lupa } from './Lupa'
import { m } from '../paraglide/messages.js'

// Message functions, called at render time so the wording follows the locale.
const LABELS: Record<InputTab, Record<EvidenceProps['mode'], () => string>> = {
  text: { searching: m.verdict_evidence_text_searching, found: m.verdict_evidence_text_found },
  url: { searching: m.verdict_evidence_url_searching, found: m.verdict_evidence_url_found },
  image: { searching: m.verdict_evidence_image_searching, found: m.verdict_evidence_image_found },
}

interface EvidenceProps {
  evidence: EvidenceData
  mode: 'searching' | 'found'
  level?: ThreatLevel
}

// What the person pasted, with the magnifier on top: roaming while investigating,
// resting in the corner with the verdict color when done.
export function Evidence({ evidence, mode, level }: EvidenceProps) {
  const label = LABELS[evidence.tab][mode]()
  return (
    <div className="evidence">
      <div className="card">
        <span className="evidence__label">{label}</span>
        {evidence.imageB64 && <img src={evidence.imageB64} alt="" className="evidence__thumb" />}
        {evidence.content && (
          <span className="evidence__text" data-tab={evidence.tab}>
            {evidence.content}
          </span>
        )}
      </div>
      <Lupa size="md" mode={mode} level={mode === 'found' ? level : undefined} />
    </div>
  )
}
