import { useState } from 'react'
import { buildConfigLink, type Preferences } from '../prefs/preferences'

// The relative sets things up on their own phone or computer and sends the link (WhatsApp etc.).
export function ShareConfigButton({ prefs }: { prefs: Preferences }) {
  const [status, setStatus] = useState<'idle' | 'shared' | 'copied' | 'failed'>('idle')

  const handleShare = async () => {
    const url = buildConfigLink(prefs)
    const text = 'Abra este link no celular ou computador que você usa para o Verifica ficar ajustado para você.'
    try {
      if (navigator.share) {
        await navigator.share({ title: 'Ajustes do Verifica', text, url })
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
          Link copiado. Cole no WhatsApp: ao abrir no aparelho da pessoa, os ajustes são aplicados sozinhos.
        </p>
      )}
      {status === 'shared' && (
        <p className="note" role="status">
          Link enviado. Ao abrir no aparelho da pessoa, os ajustes são aplicados sozinhos.
        </p>
      )}
      {status === 'failed' && (
        <p className="field-error" role="alert">
          Não deu para gerar o link neste navegador. Você pode ajustar direto no aparelho da pessoa.
        </p>
      )}
      <button type="button" className="btn btn-outline" onClick={handleShare}>
        Enviar ajustes por link
      </button>
    </div>
  )
}
