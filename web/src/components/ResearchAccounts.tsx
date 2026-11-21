import { useState, type FormEvent } from 'react'
import { canBlock, lastAccessDay } from '../domain/researchAccess'
import { useResearchAccounts, type AccountsList, type InviteState } from '../hooks/useResearchAccounts'
import { m } from '../paraglide/messages.js'
import type { AccountErrorKind, InviteRequest } from '../services/researchAccounts'
import { useResearchRoles } from '../hooks/useResearchRoles'
import type { ResearchAccount, ResearchAccountStatus, ResearchRole } from '../types'
import { ResearchRolesPanel } from './ResearchRolesPanel'

interface Props {
  currentEmail: string
  onSignedOut: () => void
}

const STATUS_LABELS: Record<ResearchAccountStatus, () => string> = {
  active: m.research_status_active,
  invited: m.research_status_invited,
  expired: m.research_status_expired,
  disabled: m.research_status_disabled,
}

const BLOCK_ERRORS: Record<AccountErrorKind, () => string> = {
  self: m.research_accounts_block_self,
  not_found: m.research_accounts_block_not_found,
  failed: m.research_accounts_block_failed,
}

// Admin screen: the invite link is copied and sent by hand, so no e-mail service is needed.
export function ResearchAccounts({ currentEmail, onSignedOut }: Props) {
  const { list, invite, blockError, sendInvite, block } = useResearchAccounts(onSignedOut)
  const roles = useResearchRoles(onSignedOut)
  const roleOptions = roles.list.status === 'ready' ? roles.list.roles : []

  return (
    <section className="app-main" aria-labelledby="contas-titulo">
      <header className="stack">
        <p className="text-small text-muted">{m.research_area()}</p>
        <h1 className="title-l" id="contas-titulo">
          {m.research_accounts_title()}
        </h1>
        <p className="text-muted">{m.research_accounts_intro()}</p>
      </header>

      <InviteForm state={invite} roles={roleOptions} onSubmit={sendInvite} />

      <section className="stack" aria-labelledby="contas-lista">
        <h2 className="title-m" id="contas-lista">
          {m.research_accounts_list_heading()}
        </h2>
        {blockError && (
          <p className="field-error" role="alert">
            {BLOCK_ERRORS[blockError]()}
          </p>
        )}
        <AccountTable list={list} currentEmail={currentEmail} onBlock={block} />
      </section>

      <ResearchRolesPanel list={roles.list} onCreate={roles.create} onUpdate={roles.update} />
    </section>
  )
}

interface InviteFormProps {
  state: InviteState
  roles: ResearchRole[]
  onSubmit: (request: InviteRequest) => void
}

// The researcher role is the default: the least an invited person needs to read the study.
const DEFAULT_ROLE_ID = 'researcher'

function InviteForm({ state, roles, onSubmit }: InviteFormProps) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState(DEFAULT_ROLE_ID)
  const [expiresOn, setExpiresOn] = useState('')

  const submit = (event: FormEvent) => {
    event.preventDefault()
    onSubmit({ email, role, expiresOn })
  }

  return (
    <form className="card stack" onSubmit={submit} aria-labelledby="convite-titulo">
      <h2 className="title-m" id="convite-titulo">
        {m.research_accounts_invite_heading()}
      </h2>

      <label htmlFor="convite-email" className="field-label">
        {m.research_accounts_email()}
      </label>
      <input id="convite-email" className="field" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />

      <label htmlFor="convite-cargo" className="field-label">
        {m.research_accounts_role()}
      </label>
      <select id="convite-cargo" className="field" value={role} onChange={(e) => setRole(e.target.value)}>
        {roles.map((r) => (
          <option key={r.id} value={r.id}>
            {r.name}
          </option>
        ))}
      </select>

      <label htmlFor="convite-ultimo-dia" className="field-label">
        {m.research_accounts_last_day()}
      </label>
      <input id="convite-ultimo-dia" className="field" type="date" value={expiresOn} onChange={(e) => setExpiresOn(e.target.value)} />

      {state.status === 'failed' && (
        <p className="field-error" role="alert">
          {m.research_accounts_invite_failed()}
        </p>
      )}

      <button type="submit" className="btn btn-primary" disabled={state.status === 'sending'}>
        {state.status === 'sending' ? m.research_accounts_inviting() : m.research_accounts_invite_submit()}
      </button>

      {state.status === 'ready' && <InviteLink email={state.email} url={state.url} />}
    </form>
  )
}

function InviteLink({ email, url }: { email: string; url: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => navigator.clipboard.writeText(url).then(() => setCopied(true))

  return (
    <div className="stack">
      <label htmlFor="convite-link" className="field-label">
        {m.research_accounts_link_label({ email })}
      </label>
      {/* Read-only and selected on focus: if the clipboard is blocked, the link can still be copied by hand. */}
      <input id="convite-link" className="field" readOnly value={url} onFocus={(e) => e.target.select()} />
      <button type="button" className="btn btn-outline" onClick={copy}>
        {m.research_accounts_copy()}
      </button>
      <p className="text-small" role="status">
        {copied && m.research_accounts_copied()}
      </p>
    </div>
  )
}

interface TableProps {
  list: AccountsList
  currentEmail: string
  onBlock: (email: string) => void
}

function AccountTable({ list, currentEmail, onBlock }: TableProps) {
  if (list.status === 'loading') return <p role="status">{m.research_accounts_loading()}</p>
  if (list.status === 'failed') return <p role="alert">{m.research_accounts_load_failed()}</p>

  return (
    <div className="research-table-wrap">
      <table className="research-table">
        <thead>
          <tr>
            <th scope="col">{m.research_accounts_col_email()}</th>
            <th scope="col">{m.research_accounts_col_role()}</th>
            <th scope="col">{m.research_accounts_col_status()}</th>
            <th scope="col">{m.research_accounts_col_until()}</th>
            <th scope="col">{m.research_accounts_col_actions()}</th>
          </tr>
        </thead>
        <tbody>
          {list.accounts.map((account) => (
            <AccountRow key={account.email} account={account} currentEmail={currentEmail} onBlock={onBlock} />
          ))}
        </tbody>
      </table>
    </div>
  )
}

function AccountRow({ account, currentEmail, onBlock }: { account: ResearchAccount } & Omit<TableProps, 'list'>) {
  const confirmBlock = () => {
    if (window.confirm(m.research_accounts_block_confirm({ email: account.email }))) onBlock(account.email)
  }

  return (
    <tr>
      <th scope="row">{account.email}</th>
      <td>{account.role.name}</td>
      <td>{STATUS_LABELS[account.status]()}</td>
      <td>{account.expires_at ? lastAccessDay(account.expires_at).toLocaleDateString() : m.research_accounts_no_end()}</td>
      <td>
        {canBlock(account, currentEmail) && (
          <button
            type="button"
            className="btn btn-outline"
            onClick={confirmBlock}
            aria-label={m.research_accounts_block_label({ email: account.email })}
          >
            {m.research_accounts_block()}
          </button>
        )}
      </td>
    </tr>
  )
}
