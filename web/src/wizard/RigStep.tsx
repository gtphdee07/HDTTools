import { useState } from 'react';
import type { RecentRig } from '../types';
import { Button } from '../design-system/Button';

interface RigStepProps {
  recentRigs: RecentRig[];
  onSelectExisting: (rig: RecentRig) => void;
  onStartNew: (nickname: string) => void;
}

export function RigStep({ recentRigs, onSelectExisting, onStartNew }: RigStepProps) {
  const [nickname, setNickname] = useState('');

  return (
    <div
      style={{
        background: 'var(--surface-card)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-md)',
        padding: 32,
        maxWidth: 560,
      }}
    >
      <h2 style={{ fontSize: 'var(--text-h2)', margin: '0 0 6px' }}>Which rig are you checking?</h2>
      <p style={{ color: 'var(--fg-2)', fontSize: 14, margin: '0 0 20px' }}>
        Pick a recent rig — we'll skip straight to the scale ticket since its tag data doesn't
        change trip to trip — or tell us about a new one.
      </p>

      {recentRigs.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>
          {recentRigs.map((rig) => {
            const subtitle = [rig.truck.manufacturer, rig.trailer.manufacturer].filter(Boolean).join(' + ');
            return (
              <div
                key={rig.nickname}
                onClick={() => onSelectExisting(rig)}
                style={{
                  border: '2px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px 16px',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15 }}>
                    {rig.nickname}
                  </div>
                  {subtitle && <div style={{ fontSize: 13, color: 'var(--fg-2)' }}>{subtitle}</div>}
                </div>
                <span style={{ fontSize: 12, color: 'var(--accent-secondary-hover)', fontWeight: 700 }}>
                  CHOOSE
                </span>
              </div>
            );
          })}
        </div>
      )}

      <label style={{ display: 'flex', flexDirection: 'column', gap: 5, marginBottom: 20 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg-2)' }}>Name a new rig</span>
        <input
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          placeholder="e.g. Big Blue"
        />
      </label>

      <Button
        variant="primary"
        size="md"
        onClick={() => onStartNew(nickname.trim())}
        disabled={!nickname.trim()}
      >
        Start New Rig
      </Button>
    </div>
  );
}
