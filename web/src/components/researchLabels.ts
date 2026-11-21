import { m } from '../paraglide/messages.js'
import type { ResearchPermission } from '../types'

// Role names are data the admins type; only the permissions have fixed wording.
export const PERMISSION_LABELS: Record<ResearchPermission, { label: () => string; hint: () => string }> = {
  view_study: { label: m.research_permission_view_study, hint: m.research_permission_view_study_hint },
  run_study: { label: m.research_permission_run_study, hint: m.research_permission_run_study_hint },
  manage_access: { label: m.research_permission_manage_access, hint: m.research_permission_manage_access_hint },
  unlimited_explain: {
    label: m.research_permission_unlimited_explain,
    hint: m.research_permission_unlimited_explain_hint,
  },
}
