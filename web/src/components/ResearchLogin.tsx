import { useEffect, useRef, useState, type FormEvent } from 'react'
import { retryMinutes } from '../domain/researchAccess'
import { m } from '../paraglide/messages.js'
import { LoginError, login } from '../services/researchAuth'
import type { ResearchUser } from '../types'
import { BackIcon } from './Icons'

interface Props {
  onSignedIn: (user: ResearchUser) => void
  onBack: () => void
}

function loginErrorText(error: LoginError): string {
  if (error.kind === 'invalid') return m.research_login_invalid()
  if (error.kind === 'throttled') return m.research_login_throttled({ minutes: retryMinutes(error.retryAfterSeconds) })
  return m.research_login_failed()
}

export function ResearchLogin({ onSignedIn, onBack }: Props) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      onSignedIn(await login(email, password))
    } catch (err) {
      setError(loginErrorText(err instanceof LoginError ? err : new LoginError('failed')))
      setSubmitting(false)
    }
  }

  return (
    <section className="app-main" aria-labelledby="entrar-titulo">
      <button type="button" className="btn btn-quiet align-start" onClick={onBack}>
        <BackIcon size={22} />
        {m.research_back()}
      </button>

      <form className="card stack stack-roomy auth-card" onSubmit={submit}>
        <h1 className="title-l" id="entrar-titulo" ref={headingRef} tabIndex={-1}>
          {m.research_login_title()}
        </h1>
        <p className="text-muted">{m.research_login_intro()}</p>

        <label htmlFor="entrar-email" className="field-label">
          {m.research_login_email()}
        </label>
        <input
          id="entrar-email"
          className="field"
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <label htmlFor="entrar-senha" className="field-label">
          {m.research_login_password()}
        </label>
        <input
          id="entrar-senha"
          className="field"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {error && (
          <p className="field-error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? m.research_login_submitting() : m.research_login_submit()}
        </button>
      </form>
    </section>
  )
}
