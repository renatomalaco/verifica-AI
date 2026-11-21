import { useEffect, useState } from 'react'
import { createRole, listRoles, RoleError, updateRole, type RoleDraft, type RoleErrorKind } from '../services/researchAccounts'
import { SignedOutError } from '../services/researchAuth'
import type { ResearchRole } from '../types'

export type RolesList = { status: 'loading' } | { status: 'failed' } | { status: 'ready'; roles: ResearchRole[] }

// A save answers with the error to show next to its form, or null when it worked.
export type SaveRole = (draft: RoleDraft) => Promise<RoleErrorKind | null>

// Admin use case: the roles of the research area and what each one may do.
export function useResearchRoles(onSignedOut: () => void) {
  const [list, setList] = useState<RolesList>({ status: 'loading' })
  const [version, setVersion] = useState(0)

  useEffect(() => {
    let active = true
    listRoles()
      .then((roles) => active && setList({ status: 'ready', roles }))
      .catch((err: Error) => {
        if (!active) return
        if (err instanceof SignedOutError) return onSignedOut()
        setList({ status: 'failed' })
      })
    return () => {
      active = false
    }
  }, [onSignedOut, version])

  const saved = async (saving: Promise<ResearchRole>): Promise<RoleErrorKind | null> => {
    try {
      await saving
      return null
    } catch (err) {
      if (err instanceof SignedOutError) onSignedOut()
      return err instanceof RoleError ? err.kind : 'failed'
    } finally {
      setVersion((v) => v + 1)
    }
  }

  const create: SaveRole = (draft) => saved(createRole(draft))
  const update = (id: string): SaveRole => (draft) => saved(updateRole(id, draft))

  return { list, create, update }
}
