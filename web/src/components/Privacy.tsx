import { useEffect, useRef, useState, type ReactNode } from 'react'
import { m } from '../paraglide/messages.js'
import { usePreferences } from '../prefs/context'
import { DEFAULT_PREFERENCES } from '../prefs/preferences'
import { BackIcon } from './Icons'

interface PrivacyProps {
  onBack: () => void
}

// Everything here must match what the backend actually does:
// migrations/0001 and 0003 (what is stored), domain/quota.py and settings (limits and retention).
export function Privacy({ onBack }: PrivacyProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  const [cleared, setCleared] = useState(false)
  const { replace } = usePreferences()

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  const clearDevice = () => {
    try {
      Object.keys(window.localStorage)
        .filter((k) => k.startsWith('vf.'))
        .forEach((k) => window.localStorage.removeItem(k))
    } catch {
      // No storage: nothing was saved.
    }
    replace({ ...DEFAULT_PREFERENCES })
    setCleared(true)
  }

  return (
    <article className="app-main" aria-labelledby="privacidade-titulo">
      <button type="button" className="btn btn-quiet align-start" onClick={onBack}>
        <BackIcon size={22} />
        {m.common_back()}
      </button>

      <div className="stack">
        <h1 className="title-l" id="privacidade-titulo" ref={headingRef} tabIndex={-1}>
          {m.privacy_title()}
        </h1>
        <p className="text-muted">{m.privacy_intro()}</p>
      </div>

      <PrivacySection title={m.privacy_not_stored_title()}>
        <ul className="bullet-list bullet-list--ok">
          <li>{m.privacy_not_stored_content()}</li>
          <li>{m.privacy_not_stored_identity()}</li>
          <li>{m.privacy_not_stored_ip()}</li>
        </ul>
      </PrivacySection>

      <PrivacySection title={m.privacy_stored_title()}>
        <p>{m.privacy_stored_intro()}</p>
        <ul className="bullet-list bullet-list--ok">
          <li>{m.privacy_stored_type()}</li>
          <li>{m.privacy_stored_message_code()}</li>
          <li>{m.privacy_stored_timing()}</li>
          <li>
            {m.privacy_stored_fingerprint_lead()} <strong>{m.privacy_stored_fingerprint_term()}</strong>{' '}
            {m.privacy_stored_fingerprint_text()}
          </li>
        </ul>
        <p>
          <strong>{m.privacy_purpose_label()}</strong> {m.privacy_purpose_text()}
        </p>
      </PrivacySection>

      <PrivacySection title={m.privacy_during_title()}>
        <ul className="bullet-list bullet-list--ok">
          <li>{m.privacy_during_masking()}</li>
          <li>{m.privacy_during_isolated_browser()}</li>
        </ul>
      </PrivacySection>

      <PrivacySection title={m.privacy_quota_title()}>
        <p>{m.privacy_quota_text()}</p>
      </PrivacySection>

      <PrivacySection title={m.privacy_device_title()}>
        <p>{m.privacy_device_text()}</p>
        {cleared ? (
          <p className="note" role="status">
            {m.privacy_device_cleared()}
          </p>
        ) : (
          <button type="button" className="btn btn-outline" onClick={clearDevice}>
            {m.privacy_device_clear()}
          </button>
        )}
      </PrivacySection>

      <p className="text-muted text-small">{m.privacy_lgpd()}</p>
    </article>
  )
}

function PrivacySection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="card stack stack-roomy">
      <h2 className="title-m">{title}</h2>
      {children}
    </section>
  )
}
