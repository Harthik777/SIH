import { fireEvent, render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import { SettingsPage } from './SettingsPage'

describe('SettingsPage', () => {
  it('persists the available competition-workspace preferences', () => {
    localStorage.clear()
    render(<SettingsPage theme="dark" onTheme={vi.fn()} user={{ email: 'demo@sentinel.local', role: 'analyst', mode: 'offline' }} onSignOut={vi.fn()} />)

    fireEvent.change(screen.getByLabelText('Workspace name'), { target: { value: 'Women Safety Division' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(screen.getByRole('status')).toHaveTextContent('Preferences saved on this device')
    expect(JSON.parse(localStorage.getItem('sentinel-workspace-preferences') ?? '{}')).toMatchObject({ workspaceName: 'Women Safety Division' })
  })
})
