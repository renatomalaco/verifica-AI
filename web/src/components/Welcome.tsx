import { useEffect, useRef, useState } from 'react'
import { m } from '../paraglide/messages.js'
import { usePreferences } from '../prefs/context'
import { markOnboarded, preferencesFromSituations } from '../prefs/preferences'
import { Header } from './Header'
import { Lupa } from './Lupa'
import { ShareConfigButton } from './ShareConfigButton'
import { SituationPicker } from './SituationPicker'

interface WelcomeProps {
  onContinue: () => void
  onSkip: () => void
}

// First visit: "who will use it?". Answering already counts as visited,
// so the tutorial doesn't come back if the person closes the site midway.
export function Welcome({ onContinue, onSkip }: WelcomeProps) {
  const [configuring, setConfiguring] = useState(false)

  const chooseMe = () => {
    markOnboarded()
    onContinue()
  }

  const chooseSomeoneElse = () => {
    markOnboarded()
    setConfiguring(true)
  }

  if (configuring) return <SituationCatalog onApplied={onContinue} onSkip={onSkip} />

  return (
    <div className="onboarding">
      <Header />
      <div className="hero">
        <Lupa size="lg" mode="float" />
        <div className="stack">
          <FocusedHeading>{m.onboarding_welcome_title()}</FocusedHeading>
          <p className="text-muted">{m.onboarding_welcome_lead()}</p>
        </div>
      </div>
      <div className="stack stack-actions">
        <p className="question">{m.onboarding_who_question()}</p>
        <button type="button" className="btn btn-primary" onClick={chooseMe}>
          {m.onboarding_who_self()}
        </button>
        <button type="button" className="btn btn-outline" onClick={chooseSomeoneElse}>
          {m.onboarding_who_someone_else()}
        </button>
      </div>
    </div>
  )
}

function SituationCatalog({ onApplied, onSkip }: { onApplied: () => void; onSkip: () => void }) {
  const { prefs, replace } = usePreferences()
  const [picked, setPicked] = useState<string[]>([])
  const draft = preferencesFromSituations(picked, prefs)

  const toggle = (id: string) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]))

  const apply = () => {
    replace(draft)
    onApplied()
  }

  return (
    <div className="onboarding">
      <Header trailing={<SkipButton onClick={onSkip} />} />
      <div className="stack">
        <FocusedHeading>{m.onboarding_catalog_title()}</FocusedHeading>
        <p className="text-muted">{m.onboarding_catalog_lead()}</p>
      </div>
      <SituationPicker selected={picked} onToggle={toggle} />
      <div className="stack stack-actions">
        <ShareConfigButton prefs={draft} />
        <button type="button" className="btn btn-primary" onClick={apply}>
          {m.onboarding_catalog_apply()}
        </button>
      </div>
    </div>
  )
}

export function SkipButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" className="btn btn-quiet" onClick={onClick}>
      {m.onboarding_skip()}
    </button>
  )
}

export function FocusedHeading({ children }: { children: string }) {
  const ref = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    ref.current?.focus()
  }, [children])
  return (
    <h1 className="title-l" ref={ref} tabIndex={-1}>
      {children}
    </h1>
  )
}
