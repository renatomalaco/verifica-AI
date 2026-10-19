import { useState } from 'react'
import { m } from '../paraglide/messages.js'
import { buildConfigLink, type Preferences } from '../prefs/preferences'

// The relative sets things up on their own phone or computer and sends the link (WhatsApp etc.).
export function ShareConfigButton({ prefs }: { prefs: Preferences }) {
  const [status, setStatus] = useState<'idle' | 'shared' | 'copied' | 'failed'>('idle')

  const handleShare = async () => {
    const url = buildConfigLink(prefs)
    const text = m.settings_share_text()
    try {
      if (navigator.share) {
        await navigator.share({ title: m.settings_share_title(), text, url })
        setStatus('shared')
        return
      }
      await navigator.clipboard.writeText(`${text}\n${url}`)
      setStatus('copied')
    } catch (err) {
      if ((err as Error)?.name === 'AbortError') return
      setStatus('failed')
    }
  }

  return (
    <div className="stack">
      {status === 'copied' && (
        <p className="note" role="status">
          {m.settings_share_copied()}
        </p>
      )}
      {status === 'shared' && (
        <p className="note" role="status">
          {m.settings_share_sent()}
        </p>
      )}
      {status === 'failed' && (
        <p className="field-error" role="alert">
          {m.settings_share_failed()}
        </p>
      )}
      <button type="button" className="btn btn-outline" onClick={handleShare}>
        {m.settings_share_button()}
      </button>
    </div>
  )
}
