import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ResearchAblationView } from './ResearchAblationView'
import { m } from '../paraglide/messages.js'

describe('ResearchAblationView Component', () => {
  it('renders research and ablation title and comparative table headers', () => {
    render(<ResearchAblationView onBack={vi.fn()} />)
    expect(screen.getByText(m.research_title())).toBeInTheDocument()
    expect(screen.getByText(m.research_mode_heuristic())).toBeInTheDocument()
    expect(screen.getByText(m.research_mode_cascade())).toBeInTheDocument()
  })

  it('renders LaTeX export tab and allows copying code', () => {
    render(<ResearchAblationView onBack={vi.fn()} />)
    expect(screen.getByText(m.research_latex_title())).toBeInTheDocument()
    expect(screen.getByText(m.research_copy_latex())).toBeInTheDocument()
  })

  it('calls onBack when return button is clicked', () => {
    const onBackMock = vi.fn()
    render(<ResearchAblationView onBack={onBackMock} />)
    const backBtn = screen.getByRole('button', { name: m.research_back() })
    fireEvent.click(backBtn)
    expect(onBackMock).toHaveBeenCalledTimes(1)
  })
})
