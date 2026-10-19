import type { ThreatLevel } from '../types'
import { CautionShape, SafeShape, ScamShape, UnknownShape } from './Icons'

type LupaSize = 'xs' | 'sm' | 'md' | 'lg'
type LupaMode = 'idle' | 'float' | 'searching' | 'found'

interface LupaProps {
  size?: LupaSize
  mode?: LupaMode
  level?: ThreatLevel
  className?: string
}

const SHAPES: Record<ThreatLevel, typeof ScamShape> = {
  GOLPE: ScamShape,
  CUIDADO: CautionShape,
  SEGURO: SafeShape,
  INCONCLUSIVO: UnknownShape,
}

// Direction A's signature element: decorative for screen readers,
// because the verdict is always written next to it.
export function Lupa({ size = 'lg', mode = 'idle', level, className = '' }: LupaProps) {
  const Shape = level ? SHAPES[level] : null
  const classes = [
    'lupa',
    `lupa--${size}`,
    mode === 'float' && 'lupa--float',
    mode === 'searching' && 'lupa--searching lupa--see-through',
    mode === 'found' && 'lupa--found lupa--arrive',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={classes} data-level={level} aria-hidden="true">
      <div className="lupa__glass">
        <span className="lupa__glint" />
        {Shape && <Shape className="lupa__icon" />}
      </div>
      <span className="lupa__handle" />
    </div>
  )
}
