import { useState, type FormEvent } from 'react'
import { isLockedPermission } from '../domain/researchAccess'
import type { RolesList, SaveRole } from '../hooks/useResearchRoles'
import { m } from '../paraglide/messages.js'
import type { RoleDraft, RoleErrorKind } from '../services/researchAccounts'
import { RESEARCH_PERMISSIONS, type ResearchPermission, type ResearchRole } from '../types'
import { PERMISSION_LABELS } from './researchLabels'

interface Props {
  list: RolesList
  onCreate: SaveRole
  onUpdate: (id: string) => SaveRole
}

const ROLE_ERRORS: Record<RoleErrorKind, () => string> = {
  name_taken: m.research_roles_name_taken,
  protected: m.research_roles_protected,
  not_found: m.research_roles_not_found,
  failed: m.research_roles_failed,
}

const EMPTY_ROLE: RoleDraft = { name: '', permissions: [] }

// Roles are named by the admins; the permissions are the only fixed part.
export function ResearchRolesPanel({ list, onCreate, onUpdate }: Props) {
  // A new key remounts the "new role" form, so it starts empty after each creation.
  const [created, setCreated] = useState(0)

  const create: SaveRole = async (draft) => {
    const error = await onCreate(draft)
    if (!error) setCreated((n) => n + 1)
    return error
  }

  return (
    <section className="stack" aria-labelledby="cargos-titulo">
      <h2 className="title-m" id="cargos-titulo">
        {m.research_roles_title()}
      </h2>
      <p className="text-muted">{m.research_roles_intro()}</p>

      <RoleList list={list} onUpdate={onUpdate} />

      <RoleForm
        key={created}
        initial={EMPTY_ROLE}
        label={m.research_roles_new_title()}
        submitLabel={m.research_roles_create()}
        onSave={create}
      />
    </section>
  )
}

function RoleList({ list, onUpdate }: Pick<Props, 'list' | 'onUpdate'>) {
  if (list.status === 'loading') return <p role="status">{m.research_roles_loading()}</p>
  if (list.status === 'failed') return <p role="alert">{m.research_roles_load_failed()}</p>

  return list.roles.map((role) => (
    <RoleForm
      key={role.id}
      roleId={role.id}
      initial={role}
      label={m.research_roles_edit_label({ name: role.name })}
      submitLabel={m.research_roles_save()}
      onSave={onUpdate(role.id)}
    />
  ))
}

interface RoleFormProps {
  initial: RoleDraft
  label: string
  submitLabel: string
  onSave: SaveRole
  roleId?: ResearchRole['id']
}

type Outcome = { status: 'idle' } | { status: 'saving' } | { status: 'saved' } | { status: 'failed'; error: RoleErrorKind }

function RoleForm({ initial, label, submitLabel, onSave, roleId = '' }: RoleFormProps) {
  const [name, setName] = useState(initial.name)
  const [permissions, setPermissions] = useState<ResearchPermission[]>(initial.permissions)
  const [outcome, setOutcome] = useState<Outcome>({ status: 'idle' })
  const fieldId = `cargo-${roleId || 'novo'}`

  const toggle = (permission: ResearchPermission) =>
    setPermissions((current) =>
      current.includes(permission) ? current.filter((p) => p !== permission) : [...current, permission],
    )

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setOutcome({ status: 'saving' })
    const error = await onSave({ name, permissions: RESEARCH_PERMISSIONS.filter((p) => permissions.includes(p)) })
    setOutcome(error ? { status: 'failed', error } : { status: 'saved' })
  }

  return (
    <form className="card stack" aria-label={label} onSubmit={submit}>
      <label htmlFor={`${fieldId}-nome`} className="field-label">
        {m.research_roles_name()}
      </label>
      <input
        id={`${fieldId}-nome`}
        className="field"
        required
        maxLength={60}
        value={name}
        onChange={(e) => setName(e.target.value)}
      />

      <fieldset className="stack permission-list">
        <legend className="field-label">{m.research_roles_permissions()}</legend>
        {RESEARCH_PERMISSIONS.map((permission) => (
          <label key={permission} className="permission-option">
            <input
              type="checkbox"
              checked={permissions.includes(permission)}
              disabled={isLockedPermission(roleId, permission)}
              onChange={() => toggle(permission)}
            />
            {PERMISSION_LABELS[permission]()}
          </label>
        ))}
        {isLockedPermission(roleId, 'manage_access') && <p className="text-small text-muted">{m.research_roles_locked()}</p>}
      </fieldset>

      {outcome.status === 'failed' && (
        <p className="field-error" role="alert">
          {ROLE_ERRORS[outcome.error]()}
        </p>
      )}

      <button type="submit" className="btn btn-outline" disabled={outcome.status === 'saving'}>
        {outcome.status === 'saving' ? m.research_roles_saving() : submitLabel}
      </button>
      <p className="text-small" role="status">
        {outcome.status === 'saved' && m.research_roles_saved()}
      </p>
    </form>
  )
}
