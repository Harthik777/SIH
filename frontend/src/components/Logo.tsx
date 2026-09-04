export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="logo" aria-label="Sentinel home">
      <svg className="logo-mark" viewBox="0 0 42 42" role="img" aria-hidden="true">
        <path d="M21 3 36 11.5v17L21 37 6 28.5v-17L21 3Z" fill="none" stroke="currentColor" strokeWidth="1.8" />
        <path d="m13 23 8-13 8 13-8 8-8-8Z" fill="none" stroke="currentColor" strokeWidth="1.8" />
        <circle cx="21" cy="21" r="3.4" fill="currentColor" />
      </svg>
      {!compact && <><span className="logo-word">SENTINEL</span><span className="logo-badge">AI</span></>}
    </div>
  )
}

