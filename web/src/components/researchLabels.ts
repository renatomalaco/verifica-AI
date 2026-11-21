import { m } from '../paraglide/messages.js'
import type { ResearchPermission } from '../types'

// Role names are data the admins type; only the permissions have fixed wording.
export const PERMISSION_LABELS: Record<ResearchPermission, () => string> = {
  run_study: m.research_permission_run_study,
  manage_access: m.research_permission_manage_access,
}
