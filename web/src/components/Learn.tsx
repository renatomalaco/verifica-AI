import { useEffect, useRef, useState } from 'react'
import { GOLDEN_RULES, LESSONS, loadLessonProgress, saveLessonProgress } from '../content/lessons'
import { BackIcon, CheckIcon } from './Icons'
import { LessonView } from './LessonView'
import { NumberedSteps } from './NumberedSteps'

interface LearnProps {
  onBack: () => void
  initialLessonId?: string | null
}

// "Aprenda a se proteger": a short course, one lesson per common scam,
// each ending with an "Isso é golpe?" exercise.
export function Learn({ onBack, initialLessonId = null }: LearnProps) {
  const [lessonId, setLessonId] = useState<string | null>(initialLessonId)
  const [done, setDone] = useState<string[]>(loadLessonProgress)

  const markDone = (id: string) =>
    setDone((prev) => {
      if (prev.includes(id)) return prev
      const next = [...prev, id]
      saveLessonProgress(next)
      return next
    })

  const index = LESSONS.findIndex((l) => l.id === lessonId)
  if (index >= 0) {
    const next = LESSONS[index + 1]
    return (
      <LessonView
        key={LESSONS[index].id}
        lesson={LESSONS[index]}
        position={index + 1}
        onBack={() => setLessonId(null)}
        onAnswered={() => markDone(LESSONS[index].id)}
        onNext={next ? () => setLessonId(next.id) : () => setLessonId(null)}
        nextLabel={next ? 'Próxima lição' : 'Ver todas as lições'}
      />
    )
  }

  return <LessonList done={done} onOpen={setLessonId} onBack={onBack} />
}

function LessonList({ done, onOpen, onBack }: { done: string[]; onOpen: (id: string) => void; onBack: () => void }) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  return (
    <section className="app-main" aria-labelledby="aprender-titulo">
      <button type="button" className="btn btn-quiet align-start" onClick={onBack}>
        <BackIcon size={22} />
        Voltar
      </button>

      <div className="stack">
        <h1 className="title-l" id="aprender-titulo" ref={headingRef} tabIndex={-1}>
          Aprenda a se proteger
        </h1>
        <p className="text-muted">
          Lições rápidas sobre os golpes mais comuns. Cada uma termina com um exercício para treinar o olhar.
        </p>
        <p className="text-small text-strong" aria-live="polite">
          {done.length} de {LESSONS.length} lições concluídas
        </p>
        <div className="progress" aria-hidden="true">
          <span style={{ width: `${(done.length / LESSONS.length) * 100}%` }} />
        </div>
      </div>

      <section className="rules" aria-labelledby="regras-titulo">
        <h2 className="title-m" id="regras-titulo">
          As 5 regras de ouro
        </h2>
        <NumberedSteps steps={GOLDEN_RULES} />
      </section>

      <h2 className="title-m">Lições</h2>
      <ol className="lesson-list">
        {LESSONS.map((lesson, i) => {
          const isDone = done.includes(lesson.id)
          return (
            <li key={lesson.id}>
              <button type="button" className="lesson-card" onClick={() => onOpen(lesson.id)}>
                <span className="lesson-card__num" data-done={isDone} aria-hidden="true">
                  {isDone ? <CheckIcon size={16} /> : i + 1}
                </span>
                <span className="lesson-card__body">
                  <span className="choice__title">{lesson.title}</span>
                  <span className="choice__desc">{lesson.summary}</span>
                </span>
                <span className="sr-only">{isDone ? 'Concluída' : 'Não concluída'}</span>
              </button>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
