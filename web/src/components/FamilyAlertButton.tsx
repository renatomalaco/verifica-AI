import { useState } from 'react'

export function FamilyAlertButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 3000)
    } catch {
      // No permission: the button stays available for another try.
    }
  }

  return (
    <button type="button" className="btn btn-quiet align-start reveal-2" onClick={copy}>
      {copied ? 'Copiado. Agora é só colar no WhatsApp.' : 'Avisar a família'}
    </button>
  )
}
