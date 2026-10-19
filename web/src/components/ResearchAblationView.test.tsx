import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ResearchAblationView } from './ResearchAblationView'

describe('ResearchAblationView Component', () => {
  it('renders research and ablation title and comparative table headers', () => {
    render(<ResearchAblationView onBack={vi.fn()} />)
    expect(screen.getByText(/Estudo de Ablação e Eficácia/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Modo 1/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Modo 3/i).length).toBeGreaterThanOrEqual(1)
  })

  it('renders LaTeX export tab and allows copying code', () => {
    render(<ResearchAblationView onBack={vi.fn()} />)
    expect(screen.getByText(/Tabela em Formato LaTeX/i)).toBeInTheDocument()
    expect(screen.getByText(/Copiar Código LaTeX/i)).toBeInTheDocument()
  })

  it('calls onBack when return button is clicked', () => {
    const onBackMock = vi.fn()
    render(<ResearchAblationView onBack={onBackMock} />)
    const backBtn = screen.getByRole('button', { name: /Voltar ao Scanner/i })
    fireEvent.click(backBtn)
    expect(onBackMock).toHaveBeenCalledTimes(1)
  })
})
