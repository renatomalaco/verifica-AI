import { useEffect, useRef } from 'react'
import { m } from '../paraglide/messages.js'

interface ErrorViewProps {
  message: string
  onRetry: () => void
  onBack: () => void
}

export function ErrorView({ message, onRetry, onBack }: ErrorViewProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  return (
    <section className="error-card" role="alert" aria-labelledby="erro-titulo">
      <h1 className="title-l" id="erro-titulo" ref={headingRef} tabIndex={-1}>
        {m.common_error_title()}
      </h1>
      <p>{message}</p>
      <p className="text-muted text-small">{m.common_error_meanwhile()}</p>
      <div className="btn-row">
        <button type="button" className="btn btn-outline" onClick={onBack}>
          {m.common_back()}
        </button>
        <button type="button" className="btn btn-solid" onClick={onRetry}>
          {m.common_retry()}
        </button>
      </div>
    </section>
  )
}
