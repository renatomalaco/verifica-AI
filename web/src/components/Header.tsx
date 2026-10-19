import type { ReactNode } from 'react'
import { BookIcon, HelpIcon, SlidersIcon } from './Icons'
import { Lupa } from './Lupa'

interface HeaderProps {
  onHelp?: () => void
  onSettings?: () => void
  onLearn?: () => void
  trailing?: ReactNode
}

export function Header({ onHelp, onSettings, onLearn, trailing }: HeaderProps) {
  return (
    <header className="topbar">
      <div className="brand">
        <Lupa size="xs" />
        <span>Verifica</span>
      </div>
      <div className="topbar-actions">
        {trailing}
        {onLearn && (
          <button type="button" className="btn btn-icon" onClick={onLearn} aria-label="Aprenda a se proteger">
            <BookIcon />
          </button>
        )}
        {onHelp && (
          <button type="button" className="btn btn-icon" onClick={onHelp} aria-label="Como usar">
            <HelpIcon />
          </button>
        )}
        {onSettings && (
          <button type="button" className="btn btn-icon" onClick={onSettings} aria-label="Ajustes de leitura">
            <SlidersIcon />
          </button>
        )}
      </div>
    </header>
  )
}
