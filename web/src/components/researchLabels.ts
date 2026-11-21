import { m } from '../paraglide/messages.js'
import type { ResearchPermission } from '../types'

// Role names are data the admins type; only the permissions have fixed wording.
export const PERMISSION_LABELS: Record<ResearchPermission, { label: () => string; hint: () => string }> = {
  run_study: { label: m.research_permission_run_study, hint: m.research_permission_run_study_hint },
  manage_access: { label: m.research_permission_manage_access, hint: m.research_permission_manage_access_hint },
}
