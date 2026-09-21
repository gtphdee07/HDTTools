import { Check } from 'lucide-react';

const STEP_LABELS = ['Rig', 'Truck Tag', 'Trailer Tag', 'Scale Ticket', 'Results'];

interface StepPillsProps {
  step: number;
}

export function StepPills({ step }: StepPillsProps) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', marginBottom: 32, flexWrap: 'wrap', rowGap: 12 }}>
      {STEP_LABELS.map((label, i) => {
        const completed = i < step;
        const current = i === step;
        return (
          <div key={label} style={{ display: 'flex', alignItems: 'center', flex: i < STEP_LABELS.length - 1 ? 1 : undefined }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 'var(--radius-pill)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  fontFamily: 'var(--font-display)',
                  fontWeight: 800,
                  fontSize: 14,
                  background: completed ? 'var(--accent-secondary-hover)' : current ? 'var(--accent-tertiary)' : 'var(--bg-surface)',
                  color: completed || current ? '#fff' : 'var(--fg-2)',
                  border: completed || current ? 'none' : '2px solid var(--border-strong)',
                  boxSizing: 'border-box',
                }}
              >
                {completed ? <Check size={16} /> : i + 1}
              </div>
              <span
                style={{
                  fontSize: 14,
                  fontWeight: current ? 700 : 500,
                  color: current || completed ? 'var(--fg-1)' : 'var(--fg-2)',
                  whiteSpace: 'nowrap',
                }}
              >
                {label}
              </span>
            </div>
            {i < STEP_LABELS.length - 1 && (
              <div
                style={{
                  flexGrow: 1,
                  height: 2,
                  margin: '0 12px',
                  minWidth: 16,
                  background: completed ? 'var(--accent-secondary-hover)' : 'var(--border-subtle)',
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
