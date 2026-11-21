export type ShareOutcome = 'shared' | 'whatsapp' | 'cancelled'

type OpenWindow = (url: string, target: string, features: string) => unknown

// Phones open their share sheet (WhatsApp, SMS…); without one, WhatsApp opens with the text ready.
export async function shareWithFamily(
  text: string,
  nav: Navigator = navigator,
  open: OpenWindow = (url, target, features) => window.open(url, target, features),
): Promise<ShareOutcome> {
  if (nav.share) {
    try {
      await nav.share({ text })
      return 'shared'
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return 'cancelled'
    }
  }
  open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener')
  return 'whatsapp'
}
