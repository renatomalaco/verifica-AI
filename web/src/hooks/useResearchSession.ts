import { useCallback, useEffect, useState } from 'react'
import { fetchCurrentUser, logout } from '../services/researchAuth'
import type { ResearchUser } from '../types'

export type ResearchSession =
  | { status: 'checking' }
  | { status: 'signed_out' }
  | { status: 'signed_in'; user: ResearchUser }

// Who is in the research area. The cookies are httpOnly, so the server is the only one who knows.
export function useResearchSession() {
  const [session, setSession] = useState<ResearchSession>({ status: 'checking' })

  useEffect(() => {
    let active = true
    fetchCurrentUser()
      .then((user) => active && setSession(user ? { status: 'signed_in', user } : { status: 'signed_out' }))
      .catch(() => active && setSession({ status: 'signed_out' }))
    return () => {
      active = false
    }
  }, [])

  const signedIn = (user: ResearchUser) => setSession({ status: 'signed_in', user })
  // Stable, so views can depend on it without reloading on every render.
  const sessionEnded = useCallback(() => setSession({ status: 'signed_out' }), [])
  const signOut = async () => {
    await logout()
    sessionEnded()
  }

  return { session, signedIn, signOut, sessionEnded }
}
