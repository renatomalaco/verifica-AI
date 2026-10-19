import { useEffect, useState } from 'react'
import { speakVerdict, stopSpeaking } from '../utils/speech'
import { Header } from './Header'
import { SpeakerIcon } from './Icons'
import { Lupa } from './Lupa'
import { FocusedHeading, SkipButton } from './Welcome'

const STEPS = [
  { title: 'Cole a mensagem que chegou', text: 'Copie a mensagem, o link ou tire um print. Depois cole no espaço indicado.' },
  { title: 'Aperte Conferir agora', text: 'O Verifica investiga com calma, por você. Leva só alguns segundos.' },
  { title: 'Veja o que fazer', text: 'O Verifica diz se é golpe e o que fazer agora. Se quiser, o resultado é lido em voz alta.' },
]

const SAMPLE = 'Oi mãe, troquei de número. Me manda um Pix urgente?'

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
            Passo {index + 1} de {STEPS.length}
          </p>
          <FocusedHeading>{step.title}</FocusedHeading>
          <p className="text-muted">{step.text}</p>
        </div>
        <div className="step-dots" aria-hidden="true">
          {STEPS.map((s, i) => (
            <span key={s.title} data-active={i === index} />
          ))}
        </div>
      </div>
      <div className="row-actions">
        <button
          type="button"
          className="btn btn-outline btn-icon btn-square"
          aria-label="Ouvir este passo"
          onClick={() => speakVerdict(`${step.title}. ${step.text}`)}
        >
          <SpeakerIcon />
        </button>
        <button type="button" className="btn btn-primary grow" onClick={isLast ? onFinish : () => setIndex(index + 1)}>
          {isLast ? 'Começar' : 'Próximo'}
        </button>
      </div>
    </div>
  )
}

function StepArt({ index }: { index: number }) {
  if (index === 0) {
    return (
      <div className="step-art" aria-hidden="true">
        <span className="step-art__label">O que chegou para você?</span>
        <span className="step-art__field step-art__focus">{SAMPLE}</span>
      </div>
    )
  }
  if (index === 1) {
    return (
      <div className="step-art" aria-hidden="true">
        <span className="step-art__field step-art__field--filled">{SAMPLE}</span>
        <span className="step-art__button step-art__focus">Conferir agora</span>
      </div>
    )
  }
  return (
    <div className="step-art" aria-hidden="true">
      <div className="step-art__verdict">
        <Lupa size="sm" level="GOLPE" />
        <strong>Isto é um golpe.</strong>
      </div>
      <span className="step-art__advice step-art__focus">
        <strong>Faça agora:</strong> não mande Pix. Ligue para o seu filho no número de sempre.
      </span>
    </div>
  )
}
