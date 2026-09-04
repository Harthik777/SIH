import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

const { login } = vi.hoisted(() => ({ login: vi.fn() }))
vi.mock('../api', () => ({ api: { login } }))

import { LoginPage } from './LoginPage'

describe('LoginPage', () => {
  it('authenticates the hosted workspace without exposing the password', async () => {
    login.mockResolvedValue({ email: 'analyst@sentinel.local', role: 'analyst', mode: 'authenticated' })
    const authenticated = vi.fn()
    render(<LoginPage onAuthenticated={authenticated}/>)
    const password = screen.getByLabelText('Password')
    expect(password).toHaveAttribute('type', 'password')
    fireEvent.change(password, { target: { value: 'test-password' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in securely' }))
    await waitFor(() => expect(authenticated).toHaveBeenCalledWith(expect.objectContaining({ role: 'analyst' })))
  })
})
