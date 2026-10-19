import { useEffect, useRef, useState } from 'react'
import { goldenRules, lessons, loadLessonProgress, saveLessonProgress } from '../content/lessons'
import { m } from '../paraglide/messages.js'
import { BackIcon, CheckIcon } from './Icons'
import { LessonView } from './LessonView'
import { NumberedSteps } from './NumberedSteps'

interface LearnProps {
  onBack: () => void
  initialLessonId?: string | null
}

// A short course, one lesson per common scam, each ending with a "is this a scam?" exercise.
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

  const all = lessons()
  const index = all.findIndex((l) => l.id === lessonId)
  if (index >= 0) {
    const next = all[index + 1]
    return (
      <LessonView
        key={all[index].id}
        lesson={all[index]}
        position={index + 1}
        onBack={() => setLessonId(null)}
        onAnswered={() => markDone(all[index].id)}
        onNext={next ? () => setLessonId(next.id) : () => setLessonId(null)}
        nextLabel={next ? m.learn_next_lesson() : m.learn_all_lessons_link()}
      />
    )
  }

  return <LessonList done={done} onOpen={setLessonId} onBack={onBack} />
}

function LessonList({ done, onOpen, onBack }: { done: string[]; onOpen: (id: string) => void; onBack: () => void }) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  const all = lessons()
  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  return (
    <section className="app-main" aria-labelledby="aprender-titulo">
      <button type="button" className="btn btn-quiet align-start" onClick={onBack}>
        <BackIcon size={22} />
        {m.common_back()}
      </button>

      <div className="stack">
        <h1 className="title-l" id="aprender-titulo" ref={headingRef} tabIndex={-1}>
          {m.learn_title()}
        </h1>
        <p className="text-muted">
          {m.learn_intro()}
        </p>
        <p className="text-small text-strong" aria-live="polite">
          {m.learn_progress({ done: done.length, total: all.length })}
        </p>
        <div className="progress" aria-hidden="true">
          <span style={{ width: `${(done.length / all.length) * 100}%` }} />
        </div>
      </div>

      <section className="rules" aria-labelledby="regras-titulo">
        <h2 className="title-m" id="regras-titulo">
          {m.learn_golden_rules_title()}
        </h2>
        <NumberedSteps steps={goldenRules()} />
      </section>

      <h2 className="title-m">{m.learn_lessons_title()}</h2>
      <ol className="lesson-list">
        {all.map((lesson, i) => {
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
                <span className="sr-only">{isDone ? m.learn_lesson_done() : m.learn_lesson_not_done()}</span>
              </button>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
