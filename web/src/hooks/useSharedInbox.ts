import { useEffect, useEffectEvent } from 'react'
import { SHARED_FLAG, sharedContent, type SharedContent } from '../domain/share'
import { takeShared } from '../services/shareInbox'

/** Hands over what another app shared (Web Share Target), once the service worker has stored it. */
export function useSharedInbox(onShared: (shared: SharedContent) => void): void {
  const receive = useEffectEvent(onShared)

  useEffect(() => {
    if (!new URLSearchParams(window.location.search).has(SHARED_FLAG)) return
    // A reload must not look for the same share again.
    window.history.replaceState(null, '', window.location.pathname)
    takeShared()
      .then((form) => {
        const shared = form && sharedContent(form)
        if (shared) receive(shared)
      })
      // Without the stored share, the person still has the empty home screen to pick the photo.
      .catch(() => {})
  }, [])
}
