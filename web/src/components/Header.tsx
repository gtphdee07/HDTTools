import type { Screen } from '../types';
import { Button } from '../design-system/Button';

interface HeaderProps {
  screen: Screen;
  onGoHome: () => void;
  onGoHistory: () => void;
  onStartWizard: () => void;
}

export function Header({ screen, onGoHome, onGoHistory, onStartWizard }: HeaderProps) {
  return (
    <div
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 10,
        background: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border-subtle)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div
        style={{
          maxWidth: 'var(--container-max)',
          margin: '0 auto',
          padding: '12px 32px',
          display: 'flex',
          alignItems: 'center',
          gap: 16,
        }}
      >
        <img
          src="/logo.png"
          alt="Wandering Trails, Wagging Tails"
          style={{ height: 52, width: 'auto', objectFit: 'contain', cursor: 'pointer' }}
          onClick={onGoHome}
        />
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.1 }}>
          <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 19, color: 'var(--fg-1)' }}>
            RigCheck
          </span>
          <span style={{ fontSize: 12, color: 'var(--fg-2)' }}>Weight safety, before you roll</span>
        </div>
        <div style={{ flex: 1 }} />
        <button
          onClick={onGoHome}
          style={{
            background: 'none',
            border: 'none',
            fontFamily: 'var(--font-display)',
            fontWeight: 600,
            fontSize: 14,
            color: screen === 'home' ? 'var(--accent-primary)' : 'var(--fg-1)',
            cursor: 'pointer',
            padding: '8px 4px',
          }}
        >
          Dashboard
        </button>
        <button
          onClick={onGoHistory}
          style={{
            background: 'none',
            border: 'none',
            fontFamily: 'var(--font-display)',
            fontWeight: 600,
            fontSize: 14,
            color: screen === 'history' ? 'var(--accent-primary)' : 'var(--fg-1)',
            cursor: 'pointer',
            padding: '8px 4px',
          }}
        >
          History
        </button>
        <Button variant="primary" size="sm" onClick={onStartWizard}>
          Start New Check
        </Button>
      </div>
    </div>
  );
}
