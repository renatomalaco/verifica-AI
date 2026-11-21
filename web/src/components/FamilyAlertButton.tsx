import { useState } from 'react'
import { m } from '../paraglide/messages.js'
import { shareWithFamily, type ShareOutcome } from '../utils/share'

const STATUS: Partial<Record<ShareOutcome, () => string>> = {
  shared: m.verdict_family_alert_shared,
  whatsapp: m.verdict_family_alert_whatsapp,
}

export function FamilyAlertButton({ text }: { text: string }) {
  const [outcome, setOutcome] = useState<ShareOutcome | null>(null)

  return (
    <div className="stack reveal-2">
      <button type="button" className="btn btn-outline" onClick={async () => setOutcome(await shareWithFamily(text))}>
        {m.verdict_family_alert()}
      </button>
      {/* Stays on screen: a 3-second flash of the button label was easy to miss. */}
      <p className="text-small" role="status">
        {outcome && STATUS[outcome]?.()}
      </p>
    </div>
  )
}
