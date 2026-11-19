import { useEffect, useState } from 'react'
import {
  AccountError,
  createInvite,
  disableAccount,
  listAccounts,
  type AccountErrorKind,
  type InviteRequest,
} from '../services/researchAccounts'
import { SignedOutError } from '../services/researchAuth'
import type { ResearchAccount } from '../types'

export type AccountsList = { status: 'loading' } | { status: 'failed' } | { status: 'ready'; accounts: ResearchAccount[] }

export type InviteState =
  | { status: 'idle' }
  | { status: 'sending' }
  | { status: 'failed' }
  | { status: 'ready'; email: string; url: string }

// Admin use case: who may enter the research area, plus inviting and blocking.
export function useResearchAccounts(onSignedOut: () => void) {
  const [list, setList] = useState<AccountsList>({ status: 'loading' })
  const [version, setVersion] = useState(0)
  const [invite, setInvite] = useState<InviteState>({ status: 'idle' })
  const [blockError, setBlockError] = useState<AccountErrorKind | null>(null)
  const reload = () => setVersion((v) => v + 1)

  useEffect(() => {
    let active = true
    listAccounts()
      .then((accounts) => active && setList({ status: 'ready', accounts }))
      .catch((err: Error) => {
        if (!active) return
        if (err instanceof SignedOutError) return onSignedOut()
        setList({ status: 'failed' })
      })
    return () => {
      active = false
    }
  }, [onSignedOut, version])

  // An ended session sends the whole area back to sign-in; any other error stays on screen.
  const handle = (err: unknown, showError: () => void) => (err instanceof SignedOutError ? onSignedOut() : showError())

  const sendInvite = async (request: InviteRequest) => {
    setInvite({ status: 'sending' })
    try {
      const url = await createInvite(request)
      setInvite({ status: 'ready', email: request.email, url })
      reload()
    } catch (err) {
      handle(err, () => setInvite({ status: 'failed' }))
    }
  }

  const block = async (email: string) => {
    setBlockError(null)
    try {
      await disableAccount(email)
    } catch (err) {
      handle(err, () => setBlockError(err instanceof AccountError ? err.kind : 'failed'))
    }
    reload()
  }

  return { list, invite, blockError, sendInvite, block }
}
