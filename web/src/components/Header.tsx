import type { Screen } from '../types';
import { useAuth } from '../auth';
import { Button } from '../design-system/Button';

interface HeaderProps {
  screen: Screen;
  onGoHome: () => void;
  onGoHistory: () => void;
  onStartWizard: () => void;
  onGoAccount: () => void;
  // True while a paid scan is in flight: the check cannot be left or restarted until it answers.
  locked?: boolean;
}

export function Header({ screen, onGoHome, onGoHistory, onStartWizard, onGoAccount, locked = false }: HeaderProps) {
  const { user } = useAuth();
  const navButtonLock = {
    cursor: locked ? 'not-allowed' : 'pointer',
    opacity: locked ? 0.5 : 1,
  } as const;
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
          style={{ height: 52, width: 'auto', objectFit: 'contain', cursor: locked ? 'default' : 'pointer' }}
          onClick={locked ? undefined : onGoHome}
        />
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.1 }}>
          <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 19, color: 'var(--fg-1)' }}>
            RigCheck
          </span>
          <span style={{ fontSize: 12, color: 'var(--fg-2)' }}>Weight safety, before you roll</span>
        </div>
        <div style={{ flex: 1 }} />
        <nav style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <button
            onClick={onGoHome}
            disabled={locked}
            style={{
              background: screen === 'home' ? 'var(--color-tint-purple)' : 'none',
              border: 'none',
              borderRadius: 'var(--radius-pill)',
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: 14,
              color: screen === 'home' ? 'var(--color-purple-deep)' : 'var(--fg-1)',
              ...navButtonLock,
              padding: '10px 18px',
            }}
          >
            Dashboard
          </button>
          <button
            onClick={onGoHistory}
            disabled={locked}
            style={{
              background: screen === 'history' ? 'var(--color-tint-purple)' : 'none',
              border: 'none',
              borderRadius: 'var(--radius-pill)',
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: 14,
              color: screen === 'history' ? 'var(--color-purple-deep)' : 'var(--fg-1)',
              ...navButtonLock,
              padding: '10px 18px',
            }}
          >
            History
          </button>
          <button
            onClick={onGoAccount}
            disabled={locked}
            style={{
              background: screen === 'account' ? 'var(--color-tint-purple)' : 'none',
              border: 'none',
              borderRadius: 'var(--radius-pill)',
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: 14,
              color: screen === 'account' ? 'var(--color-purple-deep)' : 'var(--fg-1)',
              ...navButtonLock,
              padding: '10px 18px',
            }}
          >
            {user ? 'Account' : 'Sign in'}
          </button>
        </nav>
        <Button variant="primary" size="sm" onClick={onStartWizard} disabled={locked}>
          Start New Check
        </Button>
      </div>
    </div>
  );
}
