import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { PreferencesContext } from './context'
import { applyPreferences, loadPreferences, parseConfigHash, savePreferences, type Preferences } from './preferences'

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<Preferences>(() => parseConfigHash(window.location.hash) ?? loadPreferences())

  useEffect(() => {
    applyPreferences(prefs)
    savePreferences(prefs)
  }, [prefs])

  const update = useCallback((patch: Partial<Preferences>) => setPrefs((p) => ({ ...p, ...patch })), [])
  const replace = useCallback((next: Preferences) => setPrefs(next), [])
  const value = useMemo(() => ({ prefs, update, replace }), [prefs, update, replace])

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>
}
