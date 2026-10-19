import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Investigating } from './Investigating'
import { StageAnnouncer } from './StageAnnouncer'
import { stageLabel } from '../domain/stages'

const evidence = { tab: 'url' as const, content: 'atualiza-banco.com', imageB64: null }

describe('Investigating', () => {
  it('shows what is being investigated and the real stages in plain language', () => {
    render(
      <Investigating
        evidence={evidence}
        stages={[
          { stage: 'triage', status: 'done' },
          { stage: 'url_cascade', status: 'started' },
        ]}
        onCancel={() => {}}
      />
    )
    expect(screen.getByRole('heading', { name: 'Investigando o link…' })).toHaveFocus()
    expect(screen.getByText('atualiza-banco.com')).toBeInTheDocument()
    expect(screen.getByText('Lendo a mensagem com atenção')).toBeInTheDocument()
    expect(screen.getByText('Investigando o link')).toBeInTheDocument()
  })

  it('lets the person cancel', () => {
    const onCancel = vi.fn()
    render(<Investigating evidence={evidence} stages={[]} onCancel={onCancel} />)
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })
})

describe('StageAnnouncer', () => {
  it('announces the stage currently in progress', () => {
    const { container } = render(
      <StageAnnouncer stages={[{ stage: 'triage', status: 'done' }, { stage: 'stage_0_cache', status: 'started' }]} />
    )
    expect(container.querySelector('[aria-live="polite"]')).toHaveTextContent('Procurando em listas de golpes conhecidos')
  })
})

describe('stageLabel', () => {
  it('falls back to a generic phrase for unknown stages', () => {
    expect(stageLabel('stage_9_futuro')).toBe('Conferindo mais um detalhe')
  })
})
