import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AcceptInvite } from './AcceptInvite'
import { MIN_PASSWORD_LENGTH } from '../domain/researchAccess'
import { m } from '../paraglide/messages.js'

function mockFetch(status: number, body: unknown = {}) {
  const fn = vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => body })
  global.fetch = fn
  return fn
}

function fill(password: string, confirmation = password) {
  fireEvent.change(screen.getByLabelText(m.research_invite_password()), { target: { value: password } })
  fireEvent.change(screen.getByLabelText(m.research_invite_confirm()), { target: { value: confirmation } })
  fireEvent.click(screen.getByRole('button', { name: m.research_invite_submit() }))
}

describe('AcceptInvite', () => {
  beforeEach(() => window.history.replaceState(null, '', '/pesquisa/convite#token=convite-123'))
  afterEach(() => vi.restoreAllMocks())

  it('removes the token from the address bar once read', () => {
    render(<AcceptInvite onDone={vi.fn()} />)
    expect(window.location.hash).toBe('')
  })

  it('saves the password and offers to sign in', async () => {
    const fetchMock = mockFetch(204)
    const onDone = vi.fn()
    render(<AcceptInvite onDone={onDone} />)

    fill('senha-da-banca-2026')

    expect(await screen.findByText(m.research_invite_done())).toBeInTheDocument()
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ token: 'convite-123', password: 'senha-da-banca-2026' })
    fireEvent.click(screen.getByRole('button', { name: m.research_invite_go_login() }))
    expect(onDone).toHaveBeenCalledTimes(1)
  })

  it('checks length and confirmation before calling the server', () => {
    const fetchMock = mockFetch(204)
    render(<AcceptInvite onDone={vi.fn()} />)

    fill('curta')
    expect(screen.getByRole('alert')).toHaveTextContent(m.research_invite_too_short({ min: MIN_PASSWORD_LENGTH }))

    fill('senha-da-banca-2026', 'senha-da-banca-2025')
    expect(screen.getByRole('alert')).toHaveTextContent(m.research_invite_mismatch())
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('explains when the invite was used or expired', async () => {
    mockFetch(400, { detail: 'invite_invalid' })
    render(<AcceptInvite onDone={vi.fn()} />)

    fill('senha-da-banca-2026')

    expect(await screen.findByRole('alert')).toHaveTextContent(m.research_invite_invalid())
  })

  it('explains when the link has no invite', () => {
    window.history.replaceState(null, '', '/pesquisa/convite')
    render(<AcceptInvite onDone={vi.fn()} />)

    expect(screen.getByText(m.research_invite_missing())).toBeInTheDocument()
    expect(screen.queryByLabelText(m.research_invite_password())).not.toBeInTheDocument()
  })
})
