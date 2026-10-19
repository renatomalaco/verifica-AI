import { useEffect, useId, useRef } from 'react'
import { usePreferences } from '../prefs/context'
import { DEFAULT_PREFERENCES, type Motion, type Preferences, type TextSize } from '../prefs/preferences'
import { Header } from './Header'
import { BackIcon, CheckIcon } from './Icons'
import { ShareConfigButton } from './ShareConfigButton'

interface SettingsProps {
  onClose: () => void
  onReplayTutorial: () => void
}

type BoolKey = 'highContrast' | 'largeTargets' | 'screenReader' | 'simpleMode' | 'autoSpeak'

const TOGGLES: { key: BoolKey; title: string; why: string }[] = [
  { key: 'largeTargets', title: 'Botões maiores', why: 'Ajuda quem tem tremor ou Parkinson.' },
  { key: 'highContrast', title: 'Mais contraste', why: 'Ajuda quem tem catarata ou enxerga pouco.' },
  { key: 'screenReader', title: 'Leitor de tela', why: 'Anuncia cada etapa e o resultado no leitor de tela.' },
  { key: 'simpleMode', title: 'Modo simples', why: 'Esconde detalhes e mostra só o que fazer.' },
  { key: 'autoSpeak', title: 'Ler o resultado sozinho', why: 'Ajuda quem tem dificuldade para ler.' },
]

const TEXT_SIZES: { value: TextSize; label: string }[] = [
  { value: 'normal', label: 'Normal' },
  { value: 'large', label: 'Grande' },
  { value: 'xlarge', label: 'Maior' },
]

const MOTIONS: { value: Motion; label: string }[] = [
  { value: 'full', label: 'Normal' },
  { value: 'reduced', label: 'Pouco' },
  { value: 'system', label: 'Do aparelho' },
]

export function Settings({ onClose, onReplayTutorial }: SettingsProps) {
  const { prefs, update, replace } = usePreferences()
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  return (
    <div className="onboarding">
      <Header />
      <button type="button" className="btn btn-quiet align-start" onClick={onClose}>
        <BackIcon size={22} />
        Voltar
      </button>
      <div className="stack">
        <h1 className="title-l" ref={headingRef} tabIndex={-1}>
          Ajustes de leitura
        </h1>
        <p className="text-muted">Tudo aqui é opcional. Escolha o que deixa o Verifica mais fácil para quem vai usar.</p>
      </div>

      <OptionGroup
        label="Tamanho da letra"
        options={TEXT_SIZES}
        value={prefs.textSize}
        onChange={(textSize) => update({ textSize })}
      />

      <div className="choice-list">
        {TOGGLES.map((t) => (
          <button
            key={t.key}
            type="button"
            role="switch"
            aria-checked={prefs[t.key]}
            className="choice"
            onClick={() => update({ [t.key]: !prefs[t.key] } as Partial<Preferences>)}
          >
            <span>
              <span className="choice__title">{t.title}</span>
              <span className="choice__desc">{t.why}</span>
            </span>
            <span className="check">
              <CheckIcon size={16} />
            </span>
          </button>
        ))}
      </div>

      <OptionGroup label="Animações" options={MOTIONS} value={prefs.motion} onChange={(motion) => update({ motion })} />

      <div className="stack stack-actions">
        <ShareConfigButton prefs={prefs} />
        <button type="button" className="btn btn-outline" onClick={onReplayTutorial}>
          Rever como usar
        </button>
        <button type="button" className="btn btn-quiet" onClick={() => replace({ ...DEFAULT_PREFERENCES })}>
          Voltar ao padrão
        </button>
      </div>
    </div>
  )
}

interface OptionGroupProps<T extends string> {
  label: string
  options: { value: T; label: string }[]
  value: T
  onChange: (value: T) => void
}

function OptionGroup<T extends string>({ label, options, value, onChange }: OptionGroupProps<T>) {
  const id = useId()
  return (
    <div className="settings-group">
      <span className="field-label" id={id}>
        {label}
      </span>
      <div className="option-row" role="radiogroup" aria-labelledby={id}>
        {options.map((o) => (
          <button key={o.value} type="button" role="radio" aria-checked={o.value === value} onClick={() => onChange(o.value)}>
            {o.label}
          </button>
        ))}
      </div>
    </div>
  )
}
