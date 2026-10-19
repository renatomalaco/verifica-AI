import type { ReactNode } from 'react'
import { BookIcon, HelpIcon, SlidersIcon } from './Icons'
import { Lupa } from './Lupa'
import { m } from '../paraglide/messages.js'

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
        <span>{m.app_name()}</span>
      </div>
      <div className="topbar-actions">
        {trailing}
        {onLearn && (
          <button type="button" className="btn btn-icon" onClick={onLearn} aria-label={m.common_learn_protect()}>
            <BookIcon />
          </button>
        )}
        {onHelp && (
          <button type="button" className="btn btn-icon" onClick={onHelp} aria-label={m.common_how_to_use()}>
            <HelpIcon />
          </button>
        )}
        {onSettings && (
          <button type="button" className="btn btn-icon" onClick={onSettings} aria-label={m.common_reading_settings()}>
            <SlidersIcon />
          </button>
        )}
      </div>
    </header>
  )
}
