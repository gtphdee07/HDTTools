import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import type { RecentRig } from '../types';
import { Button } from '../design-system/Button';

interface RigStepProps {
  recentRigs: RecentRig[];
  onSelectExisting: (rig: RecentRig) => void;
  onStartNew: (nickname: string) => void;
  // Resolves true once the Rig is gone, false if it could not be deleted and is still there.
  onDeleteRig: (rig: RecentRig) => Promise<boolean>;
}

const DOT_COLORS = ['var(--color-teal)', 'var(--color-purple)', 'var(--accent-primary)'];

export function RigStep({ recentRigs, onSelectExisting, onStartNew, onDeleteRig }: RigStepProps) {
  const [nickname, setNickname] = useState('');
  // Nickname of the Rig being asked about, being deleted, or that failed to delete.
  const [confirming, setConfirming] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteFailed, setDeleteFailed] = useState(false);

  const askToDelete = (rig: RecentRig) => {
    setConfirming(rig.nickname);
    setDeleteFailed(false);
  };
  const cancelDelete = () => {
    setConfirming(null);
    setDeleteFailed(false);
  };
  const confirmDelete = async (rig: RecentRig) => {
    setDeleting(true);
    setDeleteFailed(false);
    const deleted = await onDeleteRig(rig);
    setDeleting(false);
    if (deleted) setConfirming(null);
    else setDeleteFailed(true);
  };

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
                    {!isConfirming && (
                      <button
                        aria-label={`Delete ${rig.nickname}`}
                        title="Delete this rig"
                        onClick={(e) => {
                          e.stopPropagation();
                          askToDelete(rig);
                        }}
                        style={{
                          display: 'flex',
                          padding: 8,
                          background: 'none',
                          border: 'none',
                          color: 'var(--fg-2)',
                          cursor: 'pointer',
                        }}
                      >
                        <Trash2 size={18} aria-hidden="true" />
                      </button>
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
                {isConfirming && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '0 20px 16px' }}>
                    <div style={{ fontSize: 14, color: 'var(--fg-1)' }}>
                      Delete "{rig.nickname}"? This frees its spot in your Garage and can't be undone.
                    </div>
                    {deleteFailed && (
                      <div role="alert" style={{ fontSize: 14, color: 'var(--fg-1)' }}>
                        We couldn't delete "{rig.nickname}". It's still in your Garage; please try again.
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: 12 }}>
                      <Button variant="primary" size="sm" disabled={deleting} onClick={() => void confirmDelete(rig)}>
                        {deleting ? 'Deleting…' : 'Yes, delete'}
                      </Button>
                      <Button variant="ghost" size="sm" disabled={deleting} onClick={cancelDelete}>
                        Cancel
                      </Button>
                    </div>
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
