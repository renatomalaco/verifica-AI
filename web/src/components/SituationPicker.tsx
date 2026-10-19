import { SITUATIONS } from '../prefs/preferences'
import { CheckIcon } from './Icons'

interface SituationPickerProps {
  selected: string[]
  onToggle: (id: string) => void
}

export function SituationPicker({ selected, onToggle }: SituationPickerProps) {
  return (
    <div className="choice-list" role="group" aria-label="Situações de quem vai usar">
      {SITUATIONS.map((s) => {
        const on = selected.includes(s.id)
        return (
          <button key={s.id} type="button" className="choice" aria-pressed={on} onClick={() => onToggle(s.id)}>
            <span>
              <span className="choice__title">{s.title}</span>
              <span className="choice__desc">{s.description}</span>
            </span>
            <span className="check">
              <CheckIcon size={16} />
            </span>
          </button>
        )
      })}
    </div>
  )
}
