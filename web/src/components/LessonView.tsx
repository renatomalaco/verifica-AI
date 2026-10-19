import { useEffect, useRef, useState } from 'react'
import { LESSONS, lessonSpeechText, type Lesson } from '../content/lessons'
import { useSpeech } from '../hooks/useSpeech'
import { BackIcon, SpeakerIcon } from './Icons'
import { Lupa } from './Lupa'
import { NumberedSteps } from './NumberedSteps'

interface LessonViewProps {
  lesson: Lesson
  position: number
  onBack: () => void
  onAnswered: () => void
  onNext: () => void
  nextLabel: string
}

export function LessonView({ lesson, position, onBack, onAnswered, onNext, nextLabel }: LessonViewProps) {
  const [answer, setAnswer] = useState<boolean | null>(null)
  const speech = useSpeech(lessonSpeechText(lesson))
  const headingRef = useRef<HTMLHeadingElement>(null)
  const feedbackRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    headingRef.current?.focus()
    window.scrollTo({ top: 0 })
  }, [])

  const choose = (saysScam: boolean) => {
    setAnswer(saysScam)
    onAnswered()
    window.setTimeout(() => feedbackRef.current?.focus(), 0)
  }

  const correct = answer !== null && answer === lesson.quiz.isScam
  const level = lesson.quiz.isScam ? 'GOLPE' : 'SEGURO'

  return (
    <article className="app-main" aria-labelledby="licao-titulo">
      <button type="button" className="btn btn-quiet align-start" onClick={onBack}>
        <BackIcon size={22} />
        Todas as lições
      </button>

      <div className="stack">
        <p className="text-muted text-small text-strong">
          Lição {position} de {LESSONS.length}
        </p>
        <h1 className="title-l" id="licao-titulo" ref={headingRef} tabIndex={-1}>
          {lesson.title}
        </h1>
        <p>{lesson.howItWorks}</p>
      </div>

      <button type="button" className="btn btn-outline align-start" aria-pressed={speech.speaking} onClick={speech.toggle}>
        <SpeakerIcon size={22} />
        {speech.speaking ? 'Parar' : 'Ouvir a lição'}
      </button>

      <section className="card stack stack-roomy" aria-labelledby="sinais-titulo">
        <h2 className="title-m" id="sinais-titulo">
          Sinais de alerta
        </h2>
        <ul className="bullet-list">
          {lesson.signs.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </section>

      <section className="todo todo--static" data-level="info" aria-labelledby="fazer-titulo">
        <h2 className="title-m" id="fazer-titulo">
          O que fazer
        </h2>
        <NumberedSteps steps={lesson.doThis} />
      </section>

      <section className="stack stack-roomy" aria-labelledby="treino-titulo">
        <h2 className="title-m" id="treino-titulo">
          Treine: isso é golpe?
        </h2>
        <blockquote className="quiz-message">{lesson.quiz.message}</blockquote>
        <div className="btn-row" role="group" aria-label="Sua resposta">
          <button type="button" className="btn btn-outline" aria-pressed={answer === true} onClick={() => choose(true)}>
            É golpe
          </button>
          <button type="button" className="btn btn-outline" aria-pressed={answer === false} onClick={() => choose(false)}>
            Não parece golpe
          </button>
        </div>

        {answer !== null && (
          <div className="sheet quiz-feedback" ref={feedbackRef} tabIndex={-1} role="status">
            <div className="title-row">
              <Lupa size="sm" level={level} />
              <strong className="feedback-title">
                {correct ? 'Isso mesmo!' : 'Quase.'} {lesson.quiz.isScam ? 'É golpe.' : 'Provavelmente não é golpe.'}
              </strong>
            </div>
            <p>{lesson.quiz.explanation}</p>
          </div>
        )}
      </section>

      {answer !== null && (
        <button type="button" className="btn btn-primary" onClick={onNext}>
          {nextLabel}
        </button>
      )}
    </article>
  )
}
