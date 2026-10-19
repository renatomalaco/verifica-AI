import { useEffect, useRef, useState } from 'react'
import { lessons, lessonSpeechText, type Lesson } from '../content/lessons'
import { m } from '../paraglide/messages.js'
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
        {m.learn_all_lessons()}
      </button>

      <div className="stack">
        <p className="text-muted text-small text-strong">
          {m.learn_lesson_position({ position, total: lessons().length })}
        </p>
        <h1 className="title-l" id="licao-titulo" ref={headingRef} tabIndex={-1}>
          {lesson.title}
        </h1>
        <p>{lesson.howItWorks}</p>
      </div>

      <button type="button" className="btn btn-outline align-start" aria-pressed={speech.speaking} onClick={speech.toggle}>
        <SpeakerIcon size={22} />
        {speech.speaking ? m.learn_stop() : m.learn_listen()}
      </button>

      <section className="card stack stack-roomy" aria-labelledby="sinais-titulo">
        <h2 className="title-m" id="sinais-titulo">
          {m.learn_signs_title()}
        </h2>
        <ul className="bullet-list">
          {lesson.signs.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </section>

      <section className="todo todo--static" data-level="info" aria-labelledby="fazer-titulo">
        <h2 className="title-m" id="fazer-titulo">
          {m.learn_do_this_title()}
        </h2>
        <NumberedSteps steps={lesson.doThis} />
      </section>

      <section className="stack stack-roomy" aria-labelledby="treino-titulo">
        <h2 className="title-m" id="treino-titulo">
          {m.learn_quiz_title()}
        </h2>
        <blockquote className="quiz-message">{lesson.quiz.message}</blockquote>
        <div className="btn-row" role="group" aria-label={m.learn_quiz_answer_label()}>
          <button type="button" className="btn btn-outline" aria-pressed={answer === true} onClick={() => choose(true)}>
            {m.learn_quiz_scam()}
          </button>
          <button type="button" className="btn btn-outline" aria-pressed={answer === false} onClick={() => choose(false)}>
            {m.learn_quiz_not_scam()}
          </button>
        </div>

        {answer !== null && (
          <div className="sheet quiz-feedback" ref={feedbackRef} tabIndex={-1} role="status">
            <div className="title-row">
              <Lupa size="sm" level={level} />
              <strong className="feedback-title">
                {correct ? m.learn_feedback_correct() : m.learn_feedback_wrong()}{' '}
                {lesson.quiz.isScam ? m.learn_feedback_scam() : m.learn_feedback_not_scam()}
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
