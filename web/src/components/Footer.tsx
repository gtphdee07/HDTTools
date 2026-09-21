interface FooterProps {
  onGoHome: () => void;
  onGoHistory: () => void;
}

export function Footer({ onGoHome, onGoHistory }: FooterProps) {
  return (
    <footer
      style={{
        borderTop: '1px solid var(--border-subtle)',
        background: 'var(--bg-surface)',
        marginTop: 64,
      }}
    >
      <div
        style={{
          maxWidth: 'var(--container-max)',
          margin: '0 auto',
          padding: '32px 32px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: 20,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 18, color: 'var(--fg-1)' }}>
            RigCheck
          </span>
          <nav style={{ display: 'flex', alignItems: 'center', gap: 24, fontSize: 14 }}>
            <button
              onClick={onGoHome}
              style={{ background: 'none', border: 'none', padding: 0, color: 'var(--fg-1)', fontWeight: 500, cursor: 'pointer' }}
            >
              Dashboard
            </button>
            <button
              onClick={onGoHistory}
              style={{ background: 'none', border: 'none', padding: 0, color: 'var(--fg-1)', fontWeight: 500, cursor: 'pointer' }}
            >
              History
            </button>
          </nav>
        </div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 8,
            paddingTop: 16,
            borderTop: '1px solid var(--border-subtle)',
            fontSize: 13,
            color: 'var(--fg-2)',
          }}
        >
          <span>RigCheck is an experimental tool, not a certified safety decision.</span>
          <span>&copy; {new Date().getFullYear()} RigCheck</span>
        </div>
      </div>
    </footer>
  );
}
