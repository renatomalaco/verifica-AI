import { useEffect, useId, useRef } from 'react'
import { m } from '../paraglide/messages.js'
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
type Text = () => string

const TOGGLES: { key: BoolKey; title: Text; why: Text }[] = [
  { key: 'largeTargets', title: m.settings_toggle_large_targets_title, why: m.settings_toggle_large_targets_why },
  { key: 'highContrast', title: m.settings_toggle_high_contrast_title, why: m.settings_toggle_high_contrast_why },
  { key: 'screenReader', title: m.settings_toggle_screen_reader_title, why: m.settings_toggle_screen_reader_why },
  { key: 'simpleMode', title: m.settings_toggle_simple_mode_title, why: m.settings_toggle_simple_mode_why },
  { key: 'autoSpeak', title: m.settings_toggle_auto_speak_title, why: m.settings_toggle_auto_speak_why },
]

const TEXT_SIZES: { value: TextSize; label: Text }[] = [
  { value: 'normal', label: m.settings_text_size_normal },
  { value: 'large', label: m.settings_text_size_large },
  { value: 'xlarge', label: m.settings_text_size_xlarge },
]

const MOTIONS: { value: Motion; label: Text }[] = [
  { value: 'full', label: m.settings_motion_full },
  { value: 'reduced', label: m.settings_motion_reduced },
  { value: 'system', label: m.settings_motion_system },
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
        {m.common_back()}
      </button>
      <div className="stack">
        <h1 className="title-l" ref={headingRef} tabIndex={-1}>
          {m.settings_title()}
        </h1>
        <p className="text-muted">{m.settings_lead()}</p>
      </div>

      <OptionGroup
        label={m.settings_text_size_label()}
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
              <span className="choice__title">{t.title()}</span>
              <span className="choice__desc">{t.why()}</span>
            </span>
            <span className="check">
              <CheckIcon size={16} />
            </span>
          </button>
        ))}
      </div>

      <OptionGroup label={m.settings_motion_label()} options={MOTIONS} value={prefs.motion} onChange={(motion) => update({ motion })} />

      <div className="stack stack-actions">
        <ShareConfigButton prefs={prefs} />
        <button type="button" className="btn btn-outline" onClick={onReplayTutorial}>
          {m.settings_replay_tutorial()}
        </button>
        <button type="button" className="btn btn-quiet" onClick={() => replace({ ...DEFAULT_PREFERENCES })}>
          {m.settings_reset()}
        </button>
      </div>
    </div>
  )
}

interface OptionGroupProps<T extends string> {
  label: string
  options: { value: T; label: Text }[]
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
            {o.label()}
          </button>
        ))}
      </div>
    </div>
  )
}
