import { fireEvent, render, screen } from '@testing-library/react'
import { vi } from 'vitest'

vi.mock('./components/NetworkGraph', () => ({
  NetworkGraph: () => <div>Knowledge graph canvas</div>,
}))

import App from './App'

describe('Sentinel app', () => {
  it('renders the investigation command center', async () => {
    window.history.replaceState({}, '', '/')
    render(<App />)
    expect(await screen.findByText('Knowledge graph canvas', {}, { timeout: 5000 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Investigation overview' })).toBeInTheDocument()
    expect(screen.getByText('OPERATION CITY SHIELD')).toBeInTheDocument()
    expect(screen.getByRole('complementary', { name: 'Active investigation workflow' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Open fusion proof' }))
    expect(window.location.search).toContain('section=fusion')
  })
})
