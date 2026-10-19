import { useEffect, useRef } from 'react'

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
        A investigação não terminou.
      </h1>
      <p>{message}</p>
      <p className="text-muted text-small">Enquanto isso, não clique em links nem mande dinheiro.</p>
      <div className="btn-row">
        <button type="button" className="btn btn-outline" onClick={onBack}>
          Voltar
        </button>
        <button type="button" className="btn btn-solid" onClick={onRetry}>
          Tentar de novo
        </button>
      </div>
    </section>
  )
}
