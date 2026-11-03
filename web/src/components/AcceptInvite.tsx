import { useEffect, useState, type FormEvent } from 'react'
import { MIN_PASSWORD_LENGTH, inviteTokenFromHash, passwordProblem } from '../domain/researchAccess'
import { m } from '../paraglide/messages.js'
import { InviteError, acceptInvite, type InviteErrorKind } from '../services/researchAuth'

interface Props {
  onDone: () => void
}

type Problem = InviteErrorKind | 'mismatch'

const PROBLEM_TEXT: Record<Problem, () => string> = {
  invalid: m.research_invite_invalid,
  too_short: () => m.research_invite_too_short({ min: MIN_PASSWORD_LENGTH }),
  mismatch: m.research_invite_mismatch,
  failed: m.research_invite_failed,
}

// Page of the one-time invite link created by the CLI (/pesquisa/convite#token=…).
export function AcceptInvite({ onDone }: Props) {
  const [token] = useState(() => inviteTokenFromHash(window.location.hash))
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [problem, setProblem] = useState<Problem | null>(null)
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => {
    // Keep the secret out of the browser history once it is in memory.
    window.history.replaceState(null, '', window.location.pathname)
  }, [])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const local = passwordProblem(password, confirmation)
    setProblem(local)
    if (local || !token) return
    setSaving(true)
    try {
      await acceptInvite(token, password)
      setDone(true)
    } catch (err) {
      setProblem(err instanceof InviteError ? err.kind : 'failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="app-main" aria-labelledby="convite-titulo">
      <div className="card stack stack-roomy auth-card">
        <h1 className="title-l" id="convite-titulo">
          {m.research_invite_title()}
        </h1>
        {!token && <p>{m.research_invite_missing()}</p>}
        {token && done && <InviteAccepted onDone={onDone} />}
        {token && !done && (
          <form className="stack stack-roomy" onSubmit={submit} noValidate>
            <p className="text-muted">{m.research_invite_intro({ min: MIN_PASSWORD_LENGTH })}</p>

            <label htmlFor="convite-senha" className="field-label">
              {m.research_invite_password()}
            </label>
            <input
              id="convite-senha"
              className="field"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            <label htmlFor="convite-confirmacao" className="field-label">
              {m.research_invite_confirm()}
            </label>
            <input
              id="convite-confirmacao"
              className="field"
              type="password"
              autoComplete="new-password"
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
            />

            {problem && (
              <p className="field-error" role="alert">
                {PROBLEM_TEXT[problem]()}
              </p>
            )}

            <button type="submit" className="btn btn-primary" disabled={saving}>
              {m.research_invite_submit()}
            </button>
          </form>
        )}
      </div>
    </section>
  )
}

function InviteAccepted({ onDone }: Props) {
  return (
    <div className="stack stack-roomy">
      <p className="note" role="status">
        {m.research_invite_done()}
      </p>
      <button type="button" className="btn btn-primary" onClick={onDone}>
        {m.research_invite_go_login()}
      </button>
    </div>
  )
}
