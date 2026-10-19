import type { EvidenceData } from '../domain/investigation'
import type { InputTab, ThreatLevel } from '../types'
import { Lupa } from './Lupa'

const LABELS: Record<InputTab, { searching: string; found: string }> = {
  text: { searching: 'Mensagem que você colou', found: 'A mensagem investigada' },
  url: { searching: 'Link que você colou', found: 'O link investigado' },
  image: { searching: 'Print que você enviou', found: 'O print investigado' },
}

interface EvidenceProps {
  evidence: EvidenceData
  mode: 'searching' | 'found'
  level?: ThreatLevel
}

// What the person pasted, with the magnifier on top: roaming while investigating,
// resting in the corner with the verdict color when done.
export function Evidence({ evidence, mode, level }: EvidenceProps) {
  const label = LABELS[evidence.tab][mode]
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
