import { useRef, type KeyboardEvent } from 'react'
import { m } from '../paraglide/messages.js'
import type { InputTab } from '../types'
import { ClipboardIcon } from './Icons'
import { ImagePicker } from './ImagePicker'
import { Lupa } from './Lupa'

interface InputTabsProps {
  tab: InputTab
  onTabChange: (tab: InputTab) => void
  content: string
  onContentChange: (content: string) => void
  imageB64: string | null
  onImageChange: (imageB64: string | null) => void
  onScan: () => void
  onPrivacy?: () => void
}

const TABS: { id: InputTab; label: () => string }[] = [
  { id: 'text', label: m.home_tab_text },
  { id: 'url', label: m.home_tab_url },
  { id: 'image', label: m.home_tab_image },
]

export function InputTabs({ tab, onTabChange, content, onContentChange, imageB64, onImageChange, onScan, onPrivacy }: InputTabsProps) {
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({})

  const canSubmit = tab === 'image' ? !!imageB64 : content.trim().length > 0

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard?.readText()
      if (text) onContentChange(text)
    } catch {
      // No clipboard read permission: the person pastes manually.
    }
  }

  const handleTabKey = (e: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const delta = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
    if (!delta) return
    e.preventDefault()
    const next = TABS[(index + delta + TABS.length) % TABS.length]
    onTabChange(next.id)
    tabRefs.current[next.id]?.focus()
  }

  return (
    <section className="app-main" aria-labelledby="entrada-titulo">
      <div className="title-row">
        <Lupa size="sm" mode="float" />
        <h1 className="title-l" id="entrada-titulo">
          {m.home_title()}
        </h1>
      </div>

      <div className="segmented" role="tablist" aria-label={m.home_tabs_label()}>
        {TABS.map((t, i) => (
          <button
            key={t.id}
            ref={(el) => {
              tabRefs.current[t.id] = el
            }}
            type="button"
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls="painel-entrada"
            tabIndex={tab === t.id ? 0 : -1}
            onClick={() => onTabChange(t.id)}
            onKeyDown={(e) => handleTabKey(e, i)}
          >
            {t.label()}
          </button>
        ))}
      </div>

      <div className="stack" id="painel-entrada" role="tabpanel" aria-labelledby={`tab-${tab}`}>
        {tab === 'text' && (
          <>
            <label htmlFor="campo-mensagem" className="field-label">
              {m.home_text_label()}
            </label>
            <textarea
              id="campo-mensagem"
              className="field"
              placeholder={m.home_text_placeholder()}
              value={content}
              onChange={(e) => onContentChange(e.target.value)}
            />
            <PasteButton onClick={handlePaste} />
          </>
        )}

        {tab === 'url' && (
          <>
            <label htmlFor="campo-link" className="field-label">
              {m.home_url_label()}
            </label>
            <input
              id="campo-link"
              className="field"
              type="url"
              inputMode="url"
              autoComplete="off"
              placeholder={m.home_url_placeholder()}
              value={content}
              onChange={(e) => onContentChange(e.target.value)}
            />
            <PasteButton onClick={handlePaste} />
          </>
        )}

        {tab === 'image' && <ImagePicker imageB64={imageB64} onImageChange={onImageChange} />}
      </div>

      <button type="button" className="btn btn-primary" onClick={onScan} disabled={!canSubmit}>
        {m.home_check_now()}
      </button>
      <p className="text-muted text-small text-center">
        {m.home_privacy_note()}{' '}
        {onPrivacy && (
          <button type="button" className="link-button" onClick={onPrivacy}>
            {m.home_privacy_link()}
          </button>
        )}
      </p>
    </section>
  )
}

function PasteButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" className="btn btn-ghost align-start" onClick={onClick}>
      <ClipboardIcon size={20} />
      {m.home_paste()}
    </button>
  )
}
