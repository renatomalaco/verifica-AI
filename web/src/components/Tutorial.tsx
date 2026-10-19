import { useEffect, useState } from 'react'
import { m } from '../paraglide/messages.js'
import { speakVerdict, stopSpeaking } from '../utils/speech'
import { Header } from './Header'
import { SpeakerIcon } from './Icons'
import { Lupa } from './Lupa'
import { FocusedHeading, SkipButton } from './Welcome'

const STEPS = [
  { title: m.onboarding_tutorial_step_1_title, text: m.onboarding_tutorial_step_1_text },
  { title: m.onboarding_tutorial_step_2_title, text: m.onboarding_tutorial_step_2_text },
  { title: m.onboarding_tutorial_step_3_title, text: m.onboarding_tutorial_step_3_text },
]

export function Tutorial({ onFinish }: { onFinish: () => void }) {
  const [index, setIndex] = useState(0)
  const step = STEPS[index]
  const isLast = index === STEPS.length - 1

  useEffect(() => () => stopSpeaking(), [])

  return (
    <div className="onboarding">
      <Header trailing={<SkipButton onClick={onFinish} />} />
      <div className="hero">
        <StepArt index={index} />
        <div className="stack">
          <p className="text-muted text-small text-strong">
            {m.onboarding_tutorial_progress({ current: index + 1, total: STEPS.length })}
          </p>
          <FocusedHeading>{step.title()}</FocusedHeading>
          <p className="text-muted">{step.text()}</p>
        </div>
        <div className="step-dots" aria-hidden="true">
          {STEPS.map((_, i) => (
            <span key={i} data-active={i === index} />
          ))}
        </div>
      </div>
      <div className="row-actions">
        <button
          type="button"
          className="btn btn-outline btn-icon btn-square"
          aria-label={m.onboarding_tutorial_listen()}
          onClick={() => speakVerdict(`${step.title()}. ${step.text()}`)}
        >
          <SpeakerIcon />
        </button>
        <button type="button" className="btn btn-primary grow" onClick={isLast ? onFinish : () => setIndex(index + 1)}>
          {isLast ? m.onboarding_tutorial_start() : m.onboarding_tutorial_next()}
        </button>
      </div>
    </div>
  )
}

function StepArt({ index }: { index: number }) {
  if (index === 0) {
    return (
      <div className="step-art" aria-hidden="true">
        <span className="step-art__label">{m.onboarding_tutorial_art_field_label()}</span>
        <span className="step-art__field step-art__focus">{m.onboarding_tutorial_sample()}</span>
      </div>
    )
  }
  if (index === 1) {
    return (
      <div className="step-art" aria-hidden="true">
        <span className="step-art__field step-art__field--filled">{m.onboarding_tutorial_sample()}</span>
        <span className="step-art__button step-art__focus">{m.onboarding_tutorial_art_button()}</span>
      </div>
    )
  }
  return (
    <div className="step-art" aria-hidden="true">
      <div className="step-art__verdict">
        <Lupa size="sm" level="GOLPE" />
        <strong>{m.onboarding_tutorial_art_verdict()}</strong>
      </div>
      <span className="step-art__advice step-art__focus">
        <strong>{m.onboarding_tutorial_art_advice_title()}</strong> {m.onboarding_tutorial_art_advice()}
      </span>
    </div>
  )
}
