import { useEffect, useState, type ReactNode } from 'react'
import { Header } from './components/Header'
import { Home } from './components/Home'
import { Learn } from './components/Learn'
import { Privacy } from './components/Privacy'
import { ResearchAblationView } from './components/ResearchAblationView'
import { Settings } from './components/Settings'
import { Tutorial } from './components/Tutorial'
import { Welcome } from './components/Welcome'
import { CONFIG_HASH_PREFIX, hasOnboarded, markOnboarded } from './prefs/preferences'
import { PreferencesProvider } from './prefs/PreferencesProvider'
import { m } from './paraglide/messages.js'

type View = 'welcome' | 'tutorial' | 'home' | 'settings' | 'learn' | 'privacy' | 'research'

// Screens with their own URL, so they can be opened and shared via link.
const PATHS: Partial<Record<View, string>> = {
  learn: '/aprender',
  privacy: '/privacidade',
  research: '/pesquisa',
}

const openedFromConfigLink = () => window.location.hash.startsWith(CONFIG_HASH_PREFIX)

function initialView(): View {
  const match = Object.entries(PATHS).find(([, path]) => window.location.pathname.startsWith(path))
  if (match) return match[0] as View
  // Whoever opens the setup link was already configured by someone: go straight to the tutorial.
  if (openedFromConfigLink()) return 'tutorial'
  return hasOnboarded() ? 'home' : 'welcome'
}

function Shell() {
  const [view, setView] = useState<View>(initialView)
  const [configApplied, setConfigApplied] = useState(openedFromConfigLink)
  const [lessonId, setLessonId] = useState<string | null>(null)

  useEffect(() => {
    // PreferencesProvider already applied the setup link; just clean up the URL.
    if (openedFromConfigLink()) window.history.replaceState(null, '', window.location.pathname + window.location.search)
  }, [])

  const go = (next: View) => {
    window.history.pushState(null, '', PATHS[next] ?? '/')
    setView(next)
  }

  const goHome = () => go(hasOnboarded() ? 'home' : 'welcome')

  const finishTutorial = () => {
    markOnboarded()
    go('home')
  }

  const openLearn = (lesson: string | null = null) => {
    setLessonId(lesson)
    go('learn')
  }

  return (
    <div className={view === 'research' ? 'app app--wide' : 'app'}>
      {configApplied && <ConfigAppliedBanner onClose={() => setConfigApplied(false)} />}

      {view === 'welcome' && <Welcome onContinue={() => go('tutorial')} onSkip={finishTutorial} />}
      {view === 'tutorial' && <Tutorial onFinish={finishTutorial} />}
      {view === 'settings' && <Settings onClose={goHome} onReplayTutorial={() => go('tutorial')} />}
      {view === 'research' && <ResearchAblationView onBack={goHome} />}
      {view === 'learn' && (
        <PageWithHeader>
          <Learn onBack={goHome} initialLessonId={lessonId} />
        </PageWithHeader>
      )}
      {view === 'privacy' && (
        <PageWithHeader>
          <Privacy onBack={goHome} />
        </PageWithHeader>
      )}

      {/* Home stays mounted so the investigation isn't lost when opening Privacy or Learn. */}
      <div className="app-main" hidden={view !== 'home'}>
        <Header onLearn={() => openLearn()} onHelp={() => go('tutorial')} onSettings={() => go('settings')} />
        <main className="app-main">
          <Home onLearn={openLearn} onPrivacy={() => go('privacy')} />
        </main>
        <footer className="footer-links">
          <button type="button" className="link-button" onClick={() => go('privacy')}>
            {m.common_privacy()}
          </button>
          <button type="button" className="link-button" onClick={() => openLearn()}>
            {m.common_learn_protect()}
          </button>
        </footer>
      </div>
    </div>
  )
}

function PageWithHeader({ children }: { children: ReactNode }) {
  return (
    <>
      <Header />
      {children}
    </>
  )
}

function ConfigAppliedBanner({ onClose }: { onClose: () => void }) {
  return (
    <div className="banner" role="status">
      {m.common_config_applied()}
      <button type="button" className="btn btn-quiet" onClick={onClose}>
        {m.common_ok()}
      </button>
    </div>
  )
}

export default function App() {
  return (
    <PreferencesProvider>
      <Shell />
    </PreferencesProvider>
  )
}
