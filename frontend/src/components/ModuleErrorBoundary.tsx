import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle, Home, RefreshCw } from 'lucide-react'

const CHUNK_RETRY_KEY = 'sentinel-chunk-recovery'

function isChunkLoadFailure(error: Error) {
  return /dynamically imported module|ChunkLoadError|Loading chunk|Failed to fetch/i.test(error.message)
}

interface Props {
  children: ReactNode
  onHome: () => void
}

interface State {
  error: Error | null
}

export class ModuleErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Sentinel module render failed', error, info.componentStack)
    if (isChunkLoadFailure(error) && sessionStorage.getItem(CHUNK_RETRY_KEY) !== 'attempted') {
      sessionStorage.setItem(CHUNK_RETRY_KEY, 'attempted')
      window.location.reload()
    }
  }

  private retry = () => {
    sessionStorage.removeItem(CHUNK_RETRY_KEY)
    window.location.reload()
  }

  private goHome = () => {
    sessionStorage.removeItem(CHUNK_RETRY_KEY)
    this.setState({ error: null })
    this.props.onHome()
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <section className="module-error" role="alert">
        <span><AlertTriangle size={24}/></span>
        <div><small>RECOVERABLE MODULE ERROR</small><h1>This view could not be loaded</h1><p>Sentinel preserved the active investigation. Reload the latest interface bundle or return to the command center.</p></div>
        <div><button className="primary-button" onClick={this.retry}><RefreshCw size={16}/>Reload latest version</button><button className="secondary-button" onClick={this.goHome}><Home size={16}/>Command center</button></div>
      </section>
    )
  }
}

export { CHUNK_RETRY_KEY }
