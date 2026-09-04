import { Bell, BrainCircuit, Database, KeyRound, Moon, Save, Shield, SlidersHorizontal, Sun, Users } from 'lucide-react'
import type { AuthUser } from '../types'

export function SettingsPage({ theme, onTheme, user, onSignOut }: { theme:'dark'|'light'; onTheme:()=>void; user: AuthUser | null; onSignOut:()=>void }) {
  return (
    <div className="standard-page">
      <div className="page-heading"><div><span className="eyebrow">SYSTEM CONTROL</span><h1>Settings</h1><p>Configure your workspace, models, alerts, and access policies.</p></div><button className="primary-button"><Save size={14}/> Save changes</button></div>
      <div className="settings-layout">
        <aside className="panel settings-nav">{[
          [SlidersHorizontal,'Preferences'],[BrainCircuit,'Models & analysis'],[Bell,'Alert policy'],[Database,'Data sources'],[Users,'Team & roles'],[Shield,'Security'],[KeyRound,'API access'],
        ].map(([Icon,label],i)=>{const C=Icon as typeof Bell;return <button className={i===0?'active':''} key={label as string}><C size={16}/>{label as string}</button>})}</aside>
        <section className="panel settings-content">
          <div className="settings-section"><div><h2>Access session</h2><p>Authenticated private deployments enforce this identity and role on every API request.</p></div><label>Signed-in identity<input value={user?.email ?? 'Unavailable'} readOnly/></label><label>Effective role<input value={`${user?.role ?? 'unknown'} · ${user?.mode ?? 'unknown mode'}`} readOnly/></label>{user?.mode === 'authenticated' && <button className="secondary-button" onClick={onSignOut}>Sign out</button>}</div>
          <div className="settings-section"><div><h2>Workspace preferences</h2><p>Adjust the investigation environment for your workflow.</p></div><label>Workspace name<input defaultValue="Financial Intelligence Unit"/></label><label>Default investigation view<select><option>Command center</option><option>Knowledge graph</option><option>Alert center</option></select></label><div className="theme-setting"><span><strong>Interface theme</strong><small>Choose the most comfortable viewing mode.</small></span><div><button className={theme==='dark'?'active':''} onClick={theme==='light'?onTheme:undefined}><Moon size={15}/> Dark</button><button className={theme==='light'?'active':''} onClick={theme==='dark'?onTheme:undefined}><Sun size={15}/> Light</button></div></div></div>
          <div className="settings-section"><div><h2>Investigation defaults</h2><p>Applied when new cases and graph views are created.</p></div><label>Default graph layout<select><option>Force-directed</option><option>Hierarchical</option><option>Circular</option></select></label><label>Initial graph limit<select><option>1,000 entities</option><option>2,500 entities</option><option>5,000 entities</option></select></label><label className="switch-row"><span><strong>Show AI explanations</strong><small>Display concise rationale beside every finding.</small></span><input type="checkbox" defaultChecked/><i/></label><label className="switch-row"><span><strong>Community highlighting</strong><small>Color graph nodes by detected community.</small></span><input type="checkbox" defaultChecked/><i/></label><label className="switch-row"><span><strong>Keyboard shortcuts</strong><small>Enable command palette and graph shortcuts.</small></span><input type="checkbox" defaultChecked/><i/></label></div>
          <div className="settings-section"><div><h2>Regional settings</h2><p>Control dates, times, and exported report formats.</p></div><label>Time zone<select><option>Asia/Kolkata (UTC+05:30)</option><option>UTC</option><option>Europe/London</option></select></label><label>Date format<select><option>DD MMM YYYY</option><option>YYYY-MM-DD</option><option>MM/DD/YYYY</option></select></label></div>
        </section>
      </div>
    </div>
  )
}
