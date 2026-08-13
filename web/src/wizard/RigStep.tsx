import type { Rig } from '../types';
import { Button } from '../design-system/Button';

interface RigStepProps {
  rigs: Rig[];
  rigChoice: string;
  onSelect: (id: string) => void;
  onConfirm: () => void;
}

export function RigStep({ rigs, rigChoice, onSelect, onConfirm }: RigStepProps) {
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
        Pick a saved rig, or tell us about a new one.
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>
        {rigs.map((rig) => {
          const selected = rigChoice === rig.id;
          return (
            <div
              key={rig.id}
              onClick={() => onSelect(rig.id)}
              style={{
                border: `2px solid ${selected ? 'var(--accent-secondary)' : 'var(--border-subtle)'}`,
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
                  {rig.truckName}
                </div>
                <div style={{ fontSize: 13, color: 'var(--fg-2)' }}>{rig.trailerName}</div>
              </div>
              <span style={{ fontSize: 12, color: 'var(--accent-secondary-hover)', fontWeight: 700 }}>
                {selected ? 'SELECTED' : 'CHOOSE'}
              </span>
            </div>
          );
        })}
      </div>
      <Button variant="primary" size="md" onClick={onConfirm}>
        Continue
      </Button>
    </div>
  );
}
