import type { ScanAccess } from '../scanAccess';
import { Button } from '../design-system/Button';

interface ScanGateProps {
  access: ScanAccess;
  // Opens the Account screen, where a visitor signs in, buys Pro or buys scan packs.
  onGoAccount: () => void;
  // Loads the plan again after it failed to load.
  onRetry: () => void;
}

const plural = (n: number) => (n === 1 ? '1 scan' : `${n} scans`);

// What stands between the visitor and a scan, with the way past it; or, when they can scan, what a scan costs.
// Typing the numbers in is always open, so every message ends there.
export function ScanGate({ access, onGoAccount, onRetry }: ScanGateProps) {
  const message = messageFor(access);
  const action = actionFor(access, onGoAccount, onRetry);
  return (
    <div
      style={{
        background: 'var(--bg-surface-sunken)',
        borderRadius: 'var(--radius-md)',
        padding: 14,
        marginBottom: 16,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        flexWrap: 'wrap',
        fontSize: 14,
      }}
    >
      <span style={{ flex: '1 1 260px' }}>{message}</span>
      {action && (
        <Button variant="secondary" size="sm" onClick={action.run}>
          {action.label}
        </Button>
      )}
    </div>
  );
}

function messageFor(access: ScanAccess): string {
  switch (access.kind) {
    case 'ready':
      return `${plural(access.balance)} left. Each scan uses 1.`;
    case 'unavailable':
      return "Scanning isn't available right now. You can type the numbers in yourself.";
    case 'sign-in':
      return 'Scanning needs a RigCheck account with Pro. Sign in to have this photo read for you, or type the numbers in yourself.';
    case 'checking':
      return 'Checking your scans…';
    case 'load-failed':
      return "We couldn't check your plan.";
    case 'upgrade':
      return 'Scanning is part of RigCheck Pro. Upgrade to have this photo read for you, or type the numbers in yourself.';
    case 'no-scans':
      return "You're out of scans. Buy a scan pack to have this photo read for you, or type the numbers in yourself.";
  }
}

function actionFor(access: ScanAccess, onGoAccount: () => void, onRetry: () => void) {
  switch (access.kind) {
    case 'sign-in':
      return { label: 'Sign in to scan', run: onGoAccount };
    case 'upgrade':
      return { label: 'Upgrade to Pro', run: onGoAccount };
    case 'no-scans':
      return { label: 'Buy more scans', run: onGoAccount };
    case 'load-failed':
      return { label: 'Try again', run: onRetry };
    default:
      return null;
  }
}
