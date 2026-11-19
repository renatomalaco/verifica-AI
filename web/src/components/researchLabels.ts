import { m } from '../paraglide/messages.js'
import type { ResearchRole } from '../types'

// Shared by the side navigation and the accounts screen.
export const ROLE_LABELS: Record<ResearchRole, () => string> = {
  admin: m.research_role_admin,
  researcher: m.research_role_researcher,
}
