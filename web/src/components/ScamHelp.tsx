import { useState } from 'react'
import { ChevronIcon } from './Icons'

export function ScamHelp() {
  const [open, setOpen] = useState(false)

  return (
    <div className="stack stack-actions reveal-2">
      <button
        type="button"
        className="btn btn-ghost btn-disclosure"
        aria-expanded={open}
        aria-controls="ja-cai"
        onClick={() => setOpen((o) => !o)}
      >
        <span>Já caí nesse golpe. E agora?</span>
        <ChevronIcon size={20} className="chevron" />
      </button>
      {open && (
        <div className="sheet" id="ja-cai">
          <p>
            <strong>Ligue para o seu banco</strong> agora e conte o que aconteceu.
          </p>
          <p>
            <strong>Peça a devolução do Pix</strong> pelo aplicativo do banco. Quanto antes, melhor.
          </p>
          <p>
            <strong>Registre um boletim de ocorrência.</strong> Dá para fazer pela internet.
          </p>
          <p className="text-muted text-small">Não é culpa sua. Esse golpe engana muita gente.</p>
        </div>
      )}
    </div>
  )
}
