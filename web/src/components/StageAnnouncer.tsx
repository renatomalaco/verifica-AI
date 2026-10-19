import type { StageEntry } from '../domain/investigation'
import { stageLabel } from '../domain/stages'

// Only mounted when the screen reader option is on: announces each new stage.
export function StageAnnouncer({ stages }: { stages: StageEntry[] }) {
  const current = stages.findLast((s) => s.status === 'started')
  return (
    <p className="sr-only" aria-live="polite">
      {current ? stageLabel(current.stage) : ''}
    </p>
  )
}
