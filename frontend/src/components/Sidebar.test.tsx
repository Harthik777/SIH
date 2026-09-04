import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Sidebar } from './Sidebar'

const baseProps = {
  section: 'dashboard' as const,
  onChange: vi.fn(),
  collapsed: false,
  onCollapse: vi.fn(),
  alertCount: 0,
}

describe('Sidebar session identity', () => {
  it('labels the public deployment as a synthetic showcase', () => {
    render(<Sidebar {...baseProps} user={{ email: 'public-demo@sentinel.local', role: 'demo', mode: 'synthetic-public-demo' }} />)
    expect(screen.getByText('PD')).toBeInTheDocument()
    expect(screen.getByText('Public demo')).toBeInTheDocument()
    expect(screen.getByText('Synthetic showcase')).toBeInTheDocument()
    expect(screen.queryByText('Alex Kim')).not.toBeInTheDocument()
  })

  it('derives a private display identity from the authenticated session', () => {
    render(<Sidebar {...baseProps} user={{ email: 'harthik.mv@sentinel.local', role: 'supervisor', mode: 'authenticated' }} />)
    expect(screen.getByText('HM')).toBeInTheDocument()
    expect(screen.getByText('Harthik Mv')).toBeInTheDocument()
    expect(screen.getByText('Supervisor')).toBeInTheDocument()
  })
})
