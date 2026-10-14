import { useState } from 'react';
import type { RecentRig } from '../types';
import { Button } from '../design-system/Button';
import { RigDeleteButton, RigDeleteConfirm } from '../components/RigDelete';
import type { DeleteRig } from '../components/RigDelete';

interface RigStepProps {
  recentRigs: RecentRig[];
  onSelectExisting: (rig: RecentRig) => void;
  onStartNew: (nickname: string) => void;
  // Absent when Rigs cannot be deleted (a signed-out visitor), and then no delete control is shown.
  onDeleteRig?: DeleteRig;
}

const DOT_COLORS = ['var(--color-teal)', 'var(--color-purple)', 'var(--accent-primary)'];

export function RigStep({ recentRigs, onSelectExisting, onStartNew, onDeleteRig }: RigStepProps) {
  const [nickname, setNickname] = useState('');
  // Nickname of the Rig being asked about, being deleted, or that failed to delete.
  const [confirming, setConfirming] = useState<string | null>(null);

  return (
    <div style={{ maxWidth: 620, margin: '0 auto' }}>
      <h1 style={{ fontSize: 'var(--text-h1)', margin: '0 0 10px', color: 'var(--fg-1)' }}>
        Which rig are we checking?
      </h1>
      <p style={{ color: 'var(--fg-2)', fontSize: 'var(--text-body-lg)', margin: '0 0 24px' }}>
        Pick one you have checked before — we'll skip straight to the scale ticket since its tag
        data doesn't change trip to trip — or start a new one with a nickname.
      </p>

      {recentRigs.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 24 }}>
          {recentRigs.map((rig, i) => {
            const subtitle = [rig.truck.manufacturer, rig.trailer.manufacturer].filter(Boolean).join(' + ');
            const isConfirming = confirming === rig.nickname;
            return (
              <div
                key={rig.nickname}
                style={{
                  border: `1px solid ${isConfirming ? 'var(--border-strong)' : 'var(--border-subtle)'}`,
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--surface-card)',
                }}
              >
                <div
                  onClick={isConfirming ? undefined : () => onSelectExisting(rig)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 16,
                    minHeight: 72,
                    boxSizing: 'border-box',
                    padding: '0 20px',
                    cursor: isConfirming ? 'default' : 'pointer',
                  }}
                >
                  <div>
                    <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17 }}>
                      {rig.nickname}
                    </div>
                    {subtitle && <div style={{ fontSize: 13, color: 'var(--fg-2)' }}>{subtitle}</div>}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    {onDeleteRig && !isConfirming && (
                      <RigDeleteButton rig={rig} onAsk={() => setConfirming(rig.nickname)} />
                    )}
                    <span
                      style={{
                        width: 12,
                        height: 12,
                        flexShrink: 0,
                        borderRadius: 'var(--radius-pill)',
                        background: DOT_COLORS[i % DOT_COLORS.length],
                      }}
                    />
                  </div>
                </div>
                {isConfirming && onDeleteRig && (
                  <div style={{ padding: '0 20px 16px' }}>
                    <RigDeleteConfirm rig={rig} onDelete={onDeleteRig} onDone={() => setConfirming(null)} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div
        style={{
          border: '2px solid var(--border-strong)',
          borderRadius: 'var(--radius-md)',
          padding: 20,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--fg-1)' }}>Or start a new rig</span>
          <input
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            placeholder="e.g. Big Blue"
          />
          <span style={{ fontSize: 13, color: 'var(--fg-2)' }}>Something you'll recognize, like "the weekender."</span>
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
    </div>
  );
}
