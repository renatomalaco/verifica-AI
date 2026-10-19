import { createContext, useContext } from 'react'
import { DEFAULT_PREFERENCES, type Preferences } from './preferences'

export interface PreferencesContextValue {
  prefs: Preferences
  update: (patch: Partial<Preferences>) => void
  replace: (next: Preferences) => void
}

export const PreferencesContext = createContext<PreferencesContextValue>({
  prefs: DEFAULT_PREFERENCES,
  update: () => {},
  replace: () => {},
})

export function usePreferences(): PreferencesContextValue {
  return useContext(PreferencesContext)
}
