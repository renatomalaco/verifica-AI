import { useState, type FormEvent } from 'react'
import { isLockedPermission, peoplePerRole, togglePermission } from '../domain/researchAccess'
import type { RolesList, SaveRole } from '../hooks/useResearchRoles'
import { m } from '../paraglide/messages.js'
import type { RoleDraft, RoleErrorKind } from '../services/researchAccounts'
import { RESEARCH_PERMISSIONS, type ResearchAccount, type ResearchPermission, type ResearchRole } from '../types'
import { LockIcon } from './Icons'
import { PERMISSION_LABELS } from './researchLabels'

interface Props {
  list: RolesList
  accounts: ResearchAccount[]
  onCreate: SaveRole
  onUpdate: (id: string) => SaveRole
}

const ROLE_ERRORS: Record<RoleErrorKind, () => string> = {
  name_taken: m.research_roles_name_taken,
  protected: m.research_roles_protected,
  not_found: m.research_roles_not_found,
  failed: m.research_roles_failed,
}

type Feedback = { status: 'saved' } | { status: 'failed'; error: RoleErrorKind } | null

// A permission matrix: one row per role, one switch per permission, saved as soon as it flips.
export function ResearchRolesPanel({ list, accounts, onCreate, onUpdate }: Props) {
  const [feedback, setFeedback] = useState<Feedback>(null)
  const [creating, setCreating] = useState(false)

  const report = (error: RoleErrorKind | null) => {
    setFeedback(error ? { status: 'failed', error } : { status: 'saved' })
    return error
  }
  const update = (role: ResearchRole) => async (draft: RoleDraft) => report(await onUpdate(role.id)(draft))
  const create = async (name: string) => {
    const error = report(await onCreate({ name, permissions: [] }))
    if (!error) setCreating(false)
  }

  return (
    <section className="stack" aria-labelledby="cargos-titulo">
      <div className="section-head">
        <h2 className="title-m" id="cargos-titulo">
          {m.research_roles_title()}
        </h2>
        {!creating && (
          <button type="button" className="btn btn-outline btn-compact" onClick={() => setCreating(true)}>
            {m.research_roles_new()}
          </button>
        )}
      </div>
      <p className="text-muted">{m.research_roles_intro()}</p>

      <RolesTable list={list} people={peoplePerRole(accounts)} onUpdate={update} />

      {creating && <NewRoleForm onCreate={create} onCancel={() => setCreating(false)} />}

      {feedback?.status === 'failed' ? (
        <p className="field-error" role="alert">
          {ROLE_ERRORS[feedback.error]()}
        </p>
      ) : (
        <p className="text-small" role="status">
          {feedback?.status === 'saved' && m.research_roles_saved()}
        </p>
      )}
    </section>
  )
}

interface TableProps {
  list: RolesList
  people: Record<string, number>
  onUpdate: (role: ResearchRole) => (draft: RoleDraft) => Promise<RoleErrorKind | null>
}

function RolesTable({ list, people, onUpdate }: TableProps) {
  if (list.status === 'loading') return <p role="status">{m.research_roles_loading()}</p>
  if (list.status === 'failed') return <p role="alert">{m.research_roles_load_failed()}</p>

  return (
    <>
      <div className="research-table-wrap">
        <table className="research-table roles-table" aria-labelledby="cargos-titulo">
          <thead>
            <tr>
              <th scope="col">{m.research_roles_col_role()}</th>
              <th scope="col" className="roles-table__num">
                {m.research_roles_col_people()}
              </th>
              {RESEARCH_PERMISSIONS.map((permission) => (
                <th scope="col" key={permission} className="roles-table__permission">
                  {PERMISSION_LABELS[permission].label()}
                  <span className="roles-table__hint">{PERMISSION_LABELS[permission].hint()}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {list.roles.map((role) => (
              <RoleRow key={role.id} role={role} people={people[role.id] ?? 0} onSave={onUpdate(role)} />
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-small text-muted roles-table__note">
        <LockIcon size={16} />
        {m.research_roles_locked()}
      </p>
    </>
  )
}

interface RowProps {
  role: ResearchRole
  people: number
  onSave: (draft: RoleDraft) => Promise<RoleErrorKind | null>
}

function RoleRow({ role, people, onSave }: RowProps) {
  const [pending, setPending] = useState(false)
  const [renaming, setRenaming] = useState(false)

  const save = async (draft: RoleDraft) => {
    setPending(true)
    const error = await onSave(draft)
    setPending(false)
    return error
  }
  const rename = async (name: string) => {
    if (!(await save({ name, permissions: role.permissions }))) setRenaming(false)
  }

  return (
    <tr aria-busy={pending}>
      <th scope="row">
        {renaming ? (
          <RenameForm role={role} onRename={rename} onCancel={() => setRenaming(false)} />
        ) : (
          <span className="roles-table__name">
            {role.name}
            <button
              type="button"
              className="link-button text-small"
              aria-label={m.research_roles_rename_label({ name: role.name })}
              onClick={() => setRenaming(true)}
            >
              {m.research_roles_rename()}
            </button>
          </span>
        )}
      </th>
      <td className="roles-table__num">{people}</td>
      {RESEARCH_PERMISSIONS.map((permission) => (
        <td key={permission}>
          <PermissionSwitch
            role={role}
            permission={permission}
            disabled={pending}
            onToggle={() => save({ name: role.name, permissions: togglePermission(role.permissions, permission) })}
          />
        </td>
      ))}
    </tr>
  )
}

interface SwitchProps {
  role: ResearchRole
  permission: ResearchPermission
  disabled: boolean
  onToggle: () => void
}

function PermissionSwitch({ role, permission, disabled, onToggle }: SwitchProps) {
  const locked = isLockedPermission(role.id, permission)
  return (
    <span className="switch-cell">
      <button
        type="button"
        role="switch"
        className="switch"
        aria-checked={role.permissions.includes(permission)}
        aria-label={m.research_roles_switch_label({ permission: PERMISSION_LABELS[permission].label(), role: role.name })}
        disabled={disabled || locked}
        onClick={onToggle}
      >
        <span className="switch__thumb" />
      </button>
      {locked && (
        <>
          <LockIcon size={16} className="switch-cell__lock" />
          <span className="sr-only">{m.research_roles_locked_label()}</span>
        </>
      )}
    </span>
  )
}

function RenameForm({ role, onRename, onCancel }: { role: ResearchRole; onRename: (name: string) => void; onCancel: () => void }) {
  const [name, setName] = useState(role.name)
  const fieldId = `renomear-${role.id}`

  const submit = (event: FormEvent) => {
    event.preventDefault()
    onRename(name.trim())
  }

  return (
    <form className="inline-form" onSubmit={submit} onKeyDown={(e) => e.key === 'Escape' && onCancel()}>
      <label htmlFor={fieldId} className="sr-only">
        {m.research_roles_new_name_of({ name: role.name })}
      </label>
      <input id={fieldId} className="field field-compact" required maxLength={60} autoFocus value={name} onChange={(e) => setName(e.target.value)} />
      <button type="submit" className="btn btn-solid btn-compact">
        {m.research_roles_save_name()}
      </button>
      <button type="button" className="btn btn-quiet btn-compact" onClick={onCancel}>
        {m.research_roles_cancel()}
      </button>
    </form>
  )
}

function NewRoleForm({ onCreate, onCancel }: { onCreate: (name: string) => void; onCancel: () => void }) {
  const [name, setName] = useState('')

  const submit = (event: FormEvent) => {
    event.preventDefault()
    onCreate(name.trim())
  }

  return (
    <form className="inline-form" onSubmit={submit} onKeyDown={(e) => e.key === 'Escape' && onCancel()}>
      <label htmlFor="novo-cargo" className="sr-only">
        {m.research_roles_new_name()}
      </label>
      <input
        id="novo-cargo"
        className="field field-compact"
        required
        maxLength={60}
        autoFocus
        placeholder={m.research_roles_new_name()}
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <button type="submit" className="btn btn-solid btn-compact">
        {m.research_roles_create()}
      </button>
      <button type="button" className="btn btn-quiet btn-compact" onClick={onCancel}>
        {m.research_roles_cancel()}
      </button>
    </form>
  )
}
