import { CheckCircle2, KeyRound, MapPinned, Moon, Save, Shield, SlidersHorizontal, Sun } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import type { AuthUser } from '../types'

export function SettingsPage({ theme, onTheme, user, onSignOut }: { theme:'dark'|'light'; onTheme:()=>void; user: AuthUser | null; onSignOut:()=>void }) {
  const [activeSection, setActiveSection] = useState('workspace-preferences')
  const [saved, setSaved] = useState(false)
  const [initialPreferences] = useState<Record<string, unknown>>(() => {
    try { return JSON.parse(localStorage.getItem('sentinel-workspace-preferences') ?? '{}') }
    catch { return {} }
  })
  const textPreference = (key: string, fallback: string) => typeof initialPreferences[key] === 'string' ? initialPreferences[key] as string : fallback
  const checkedPreference = (key: string) => !(key in initialPreferences) || initialPreferences[key] === true || initialPreferences[key] === 'enabled'
  const openSection = (id: string) => {
    setActiveSection(id)
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  const save = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const values = {
      ...Object.fromEntries(form.entries()),
      showExplanations: form.has('showExplanations'),
      communityHighlighting: form.has('communityHighlighting'),
      keyboardShortcuts: form.has('keyboardShortcuts'),
    }
    localStorage.setItem('sentinel-workspace-preferences', JSON.stringify(values))
    setSaved(true)
    window.setTimeout(() => setSaved(false), 2600)
  }
  return (
    <div className="standard-page">
      <div className="page-heading"><div><span className="eyebrow">SYSTEM CONTROL</span><h1>Settings</h1><p>Configure the preferences available in this competition deployment.</p></div><button className="primary-button" type="submit" form="workspace-settings"><Save size={14}/> Save changes</button></div>
      <div className="settings-layout">
        <aside className="panel settings-nav" aria-label="Settings sections">{[
          [SlidersHorizontal,'Preferences','workspace-preferences'],[Shield,'Investigation','investigation-defaults'],[MapPinned,'Regional','regional-settings'],[KeyRound,'Access & security','access-session'],
        ].map(([Icon,label,id])=>{const C=Icon as typeof Shield;return <button type="button" className={activeSection===id?'active':''} aria-current={activeSection===id?'location':undefined} key={id as string} onClick={() => openSection(id as string)}><C size={16}/>{label as string}</button>})}</aside>
        <form className="panel settings-content" id="workspace-settings" onSubmit={save}>
          <div className="settings-section" id="workspace-preferences"><div><h2>Workspace preferences</h2><p>Adjust the investigation environment for your workflow.</p></div><label>Workspace name<input name="workspaceName" defaultValue={textPreference('workspaceName', 'Financial Intelligence Unit')}/></label><label>Default investigation view<select name="defaultView" defaultValue={textPreference('defaultView', 'Command center')}><option>Command center</option><option>Knowledge graph</option><option>Alert center</option></select></label><div className="theme-setting"><span><strong>Interface theme</strong><small>Choose the most comfortable viewing mode.</small></span><div><button type="button" className={theme==='dark'?'active':''} onClick={theme==='light'?onTheme:undefined}><Moon size={15}/> Dark</button><button type="button" className={theme==='light'?'active':''} onClick={theme==='dark'?onTheme:undefined}><Sun size={15}/> Light</button></div></div></div>
          <div className="settings-section" id="investigation-defaults"><div><h2>Investigation defaults</h2><p>Applied when new cases and graph views are created.</p></div><label>Default graph layout<select name="graphLayout" defaultValue={textPreference('graphLayout', 'Force-directed')}><option>Force-directed</option><option>Hierarchical</option><option>Circular</option></select></label><label>Initial graph limit<select name="graphLimit" defaultValue={textPreference('graphLimit', '1,000 entities')}><option>1,000 entities</option><option>2,500 entities</option><option>5,000 entities</option></select></label><label className="switch-row"><span><strong>Show explainable findings</strong><small>Display concise rationale beside every finding.</small></span><input name="showExplanations" value="enabled" type="checkbox" defaultChecked={checkedPreference('showExplanations')}/><i/></label><label className="switch-row"><span><strong>Community highlighting</strong><small>Color graph nodes by detected community.</small></span><input name="communityHighlighting" value="enabled" type="checkbox" defaultChecked={checkedPreference('communityHighlighting')}/><i/></label><label className="switch-row"><span><strong>Keyboard shortcuts</strong><small>Enable search and graph shortcuts.</small></span><input name="keyboardShortcuts" value="enabled" type="checkbox" defaultChecked={checkedPreference('keyboardShortcuts')}/><i/></label></div>
          <div className="settings-section" id="regional-settings"><div><h2>Regional settings</h2><p>Control dates, times, and exported report formats.</p></div><label>Time zone<select name="timeZone" defaultValue={textPreference('timeZone', 'Asia/Kolkata (UTC+05:30)')}><option>Asia/Kolkata (UTC+05:30)</option><option>UTC</option><option>Europe/London</option></select></label><label>Date format<select name="dateFormat" defaultValue={textPreference('dateFormat', 'DD MMM YYYY')}><option>DD MMM YYYY</option><option>YYYY-MM-DD</option><option>MM/DD/YYYY</option></select></label></div>
          <div className="settings-section" id="access-session"><div><h2>Access session</h2><p>Authenticated deployments enforce this identity and role on every protected API request.</p></div><label>Signed-in identity<input value={user?.email ?? 'Unavailable'} readOnly/></label><label>Effective role<input value={`${user?.role ?? 'unknown'} · ${user?.mode ?? 'unknown mode'}`} readOnly/></label>{user?.mode === 'authenticated' && <button type="button" className="secondary-button" onClick={onSignOut}>Sign out</button>}</div>
          <div className={`settings-save-state ${saved ? 'visible' : ''}`} role="status" aria-live="polite"><CheckCircle2 size={15}/> Preferences saved on this device</div>
        </form>
      </div>
    </div>
  )
}
