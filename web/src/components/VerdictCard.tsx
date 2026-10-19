import { useEffect, useRef } from 'react'
import { lessonForCategory } from '../content/lessons'
import type { EvidenceData } from '../domain/investigation'
import { adviceSteps, familyAlertText, offersScamHelp, spokenVerdictText, todoTitle, verdictTitle } from '../domain/verdict'
import { useExplanation } from '../hooks/useExplanation'
import { useSpeech } from '../hooks/useSpeech'
import { usePreferences } from '../prefs/context'
import type { ScanResponse } from '../types'
import { Evidence } from './Evidence'
import { ExplanationSheet } from './ExplanationSheet'
import { FamilyAlertButton } from './FamilyAlertButton'
import { BackIcon, SpeakerIcon, StopIcon } from './Icons'
import { NumberedSteps } from './NumberedSteps'
import { ScamHelp } from './ScamHelp'
import { TechDetails } from './TechDetails'

interface VerdictCardProps {
  response: ScanResponse
  evidence: EvidenceData
  onReset: () => void
  onLearn?: (lessonId: string | null) => void
  onPrivacy?: () => void
}

export function VerdictCard({ response, evidence, onReset, onLearn, onPrivacy }: VerdictCardProps) {
  const { prefs } = usePreferences()
  const { threat_level: level, verdict_plain, details } = response
  const speech = useSpeech(spokenVerdictText(response), { startOnMount: prefs.autoSpeak })
  const { explanation, toggle: toggleExplanation } = useExplanation(response.id)
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  const scamRisk = offersScamHelp(level)

  return (
    <section className="app-main" aria-labelledby="veredito-titulo">
      <button type="button" className="btn btn-quiet align-start" onClick={onReset}>
        <BackIcon size={22} />
        Conferir outra
      </button>

      <Evidence evidence={evidence} mode="found" level={level} />

      <div className="stack verdict-head">
        <h1 className="title-xl verdict-title" data-level={level} id="veredito-titulo" ref={headingRef} tabIndex={-1}>
          {verdictTitle(level)}
        </h1>
        <p>{verdict_plain}</p>
        {details.links_not_inspected && (
          <p className="text-muted text-small">O link desta mensagem não pôde ser aberto, então não dá para dizer que ele é seguro.</p>
        )}
      </div>

      <section className="todo" data-level={level} aria-labelledby="todo-titulo">
        <h2 className="title-m" id="todo-titulo">
          {todoTitle(level)}
        </h2>
        <NumberedSteps steps={adviceSteps(response.action_advice)} />
      </section>

      <div className={prefs.simpleMode ? 'reveal-1' : 'btn-row reveal-1'}>
        <button type="button" className="btn btn-outline" aria-pressed={speech.speaking} onClick={speech.toggle}>
          {speech.speaking ? <StopIcon size={22} /> : <SpeakerIcon size={22} />}
          {speech.speaking ? 'Parar' : 'Ouvir'}
        </button>
        {!prefs.simpleMode && (
          <button type="button" className="btn btn-solid" aria-expanded={explanation.status !== 'closed'} onClick={toggleExplanation}>
            {explanation.status === 'closed' ? 'Me explica' : 'Fechar'}
          </button>
        )}
      </div>

      <ExplanationSheet explanation={explanation} />

      {scamRisk && <ScamHelp />}

      {scamRisk && onLearn && (
        <button type="button" className="btn btn-quiet align-start reveal-2" onClick={() => onLearn(lessonForCategory(details.category))}>
          Aprenda a reconhecer esse tipo de golpe
        </button>
      )}

      {!prefs.simpleMode && <FamilyAlertButton text={familyAlertText(response)} />}
      {!prefs.simpleMode && <TechDetails response={response} onPrivacy={onPrivacy} />}
    </section>
  )
}
