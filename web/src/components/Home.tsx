import { useState } from 'react'
import { buildEvidence } from '../domain/investigation'
import { useInvestigation } from '../hooks/useInvestigation'
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

// Web Share Target / deep links: shared content arrives prefilled.
function readSharedContent(): { tab: InputTab; content: string } {
  const params = new URLSearchParams(window.location.search)
  const sharedUrl = params.get('url')
  const sharedText = params.get('text') || params.get('title')
  if (sharedUrl) return { tab: 'url', content: sharedUrl }
  if (sharedText) return { tab: 'text', content: sharedText }
  return { tab: 'text', content: '' }
}

export function Home({ onLearn, onPrivacy }: HomeProps) {
  const { prefs } = usePreferences()
  const [shared] = useState(readSharedContent)
  const [tab, setTab] = useState<InputTab>(shared.tab)
  const [content, setContent] = useState(shared.content)
  const [imageB64, setImageB64] = useState<string | null>(null)
  const { state, start, reset } = useInvestigation()

  // Switching between photo and text clears the field: content from one doesn't fit the other.
  const changeTab = (next: InputTab) => {
    if (next !== tab && (next === 'image' || tab === 'image')) setContent('')
    setTab(next)
  }

  const investigate = () => {
    const evidence = buildEvidence(tab, content, imageB64)
    if (evidence) start(evidence)
  }

  const startOver = () => {
    reset()
    setContent('')
    setImageB64(null)
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
        imageB64={imageB64}
        onImageChange={setImageB64}
        onScan={investigate}
        onPrivacy={onPrivacy}
      />
      <button type="button" className="learn-teaser" onClick={() => onLearn()}>
        <span className="lesson-card__num" aria-hidden="true">
          <BookIcon size={20} />
        </span>
        <span>
          <span className="choice__title">Aprenda a se proteger</span>
          <span className="choice__desc">Lições rápidas sobre os golpes mais comuns</span>
        </span>
      </button>
    </>
  )
}
