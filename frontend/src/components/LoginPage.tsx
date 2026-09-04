import { FormEvent, useState } from 'react'
import { KeyRound, LockKeyhole, ShieldCheck } from 'lucide-react'
import { api } from '../api'
import type { AuthUser } from '../types'
import { Logo } from './Logo'

export function LoginPage({ onAuthenticated }: { onAuthenticated: (user: AuthUser) => void }) {
  const [email, setEmail] = useState('analyst@sentinel.local')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      onAuthenticated(await api.login(email, password))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Authentication failed')
    } finally {
      setBusy(false)
    }
  }

  return <main className="login-page">
    <section className="login-card panel">
      <Logo />
      <span className="eyebrow"><ShieldCheck size={12}/> PRIVATE INVESTIGATION WORKSPACE</span>
      <h1>Authorized access only</h1>
      <p>Sign in with a locally configured analyst or supervisor account. Credentials and evidence stay on this deployment.</p>
      <form onSubmit={submit}>
        <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" required/></label>
        <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required/></label>
        {error && <div className="login-error" role="alert"><LockKeyhole size={14}/>{error}</div>}
        <button className="primary-button" disabled={busy}><KeyRound size={15}/>{busy ? 'Verifying…' : 'Sign in securely'}</button>
      </form>
      <small>JWT session · role-enforced APIs · tamper-evident login audit</small>
    </section>
  </main>
}
