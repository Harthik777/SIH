import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

vi.mock('./components/NetworkGraph', () => ({
  NetworkGraph: () => <div>Knowledge graph canvas</div>,
}))

import App from './App'

describe('Sentinel app', () => {
  it('renders the investigation command center', async () => {
    render(<App />)
    expect(await screen.findByText('Knowledge graph canvas')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Investigation overview' })).toBeInTheDocument()
    expect(screen.getByText('OPERATION CITY SHIELD')).toBeInTheDocument()
  })
})
