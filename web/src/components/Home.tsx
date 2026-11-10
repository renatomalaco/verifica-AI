import { useState } from 'react'
import { m } from '../paraglide/messages.js'
import { buildEvidence } from '../domain/investigation'
import { sharedContent, type SharedContent } from '../domain/share'
import { useImageInput } from '../hooks/useImageInput'
import { useInvestigation } from '../hooks/useInvestigation'
import { useSharedInbox } from '../hooks/useSharedInbox'
import { usePreferences } from '../prefs/context'
import type { InputTab } from '../types'
import { ErrorView } from './ErrorView'
import { BookIcon } from './Icons'
import { InputTabs } from './InputTabs'
import { Investigating } from './Investigating'
import { StageAnnouncer } from './StageAnnouncer'
import { VerdictCard } from './VerdictCard'

interface HomeProps {
  onLearn: (lessonId?: string | null) => void
  onPrivacy: () => void
}

// Deep links (?url=, ?text=) arrive prefilled; a photo can only come through the share inbox.
function readDeepLink(): { tab: InputTab; content: string } {
  const shared = sharedContent(new URLSearchParams(window.location.search))
  return shared && shared.tab !== 'image' ? shared : { tab: 'text', content: '' }
}

export function Home({ onLearn, onPrivacy }: HomeProps) {
  const { prefs } = usePreferences()
  const [deepLink] = useState(readDeepLink)
  const [tab, setTab] = useState<InputTab>(deepLink.tab)
  const [content, setContent] = useState(deepLink.content)
  const image = useImageInput()
  const { state, start, reset } = useInvestigation()

  // Shared from another app: lands in its tab, so the person only taps "check now".
  useSharedInbox((shared: SharedContent) => {
    setTab(shared.tab)
    if (shared.tab === 'image') image.pick(shared.file)
    else setContent(shared.content)
  })

  // Switching between photo and text clears the field: content from one doesn't fit the other.
  const changeTab = (next: InputTab) => {
    if (next !== tab && (next === 'image' || tab === 'image')) setContent('')
    setTab(next)
  }

  const investigate = () => {
    const evidence = buildEvidence(tab, content, image.imageB64)
    if (evidence) start(evidence)
  }

  const startOver = () => {
    reset()
    setContent('')
    image.clear()
  }

  if (state.status === 'scanning') {
    return (
      <>
        <Investigating evidence={state.evidence} stages={state.stages} onCancel={reset} />
        {prefs.screenReader && <StageAnnouncer stages={state.stages} />}
      </>
    )
  }

  if (state.status === 'result') {
    return <VerdictCard response={state.verdict} evidence={state.evidence} onReset={startOver} onLearn={onLearn} onPrivacy={onPrivacy} />
  }

  if (state.status === 'error') {
    return <ErrorView message={state.message} onRetry={() => start(state.evidence)} onBack={reset} />
  }

  return (
    <>
      <InputTabs
        tab={tab}
        onTabChange={changeTab}
        content={content}
        onContentChange={setContent}
        image={image}
        onScan={investigate}
        onPrivacy={onPrivacy}
      />
      <button type="button" className="learn-teaser" onClick={() => onLearn()}>
        <span className="lesson-card__num" aria-hidden="true">
          <BookIcon size={20} />
        </span>
        <span>
          <span className="choice__title">{m.home_learn_title()}</span>
          <span className="choice__desc">{m.home_learn_desc()}</span>
        </span>
      </button>
    </>
  )
}
