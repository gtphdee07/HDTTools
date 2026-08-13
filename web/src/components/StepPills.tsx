const STEP_LABELS = ['Truck Tag', 'Trailer Tag', 'Scale Ticket', 'Results'];

interface StepPillsProps {
  step: number;
}

export function StepPills({ step }: StepPillsProps) {
  return (
    <div style={{ display: 'flex', gap: 10, marginBottom: 28, flexWrap: 'wrap' }}>
      {STEP_LABELS.map((label, i) => {
        const n = i + 1;
        const active = step === n || (step === 0 && n === 1);
        return (
          <div
            key={label}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 16px',
              borderRadius: 'var(--radius-pill)',
              fontFamily: 'var(--font-display)',
              fontWeight: 600,
              fontSize: 13,
              background: active ? 'var(--accent-primary)' : 'var(--color-cream-dark)',
              color: active ? '#fff' : 'var(--fg-2)',
            }}
          >
            <span>{n}</span>
            <span>{label}</span>
          </div>
        );
      })}
    </div>
  );
}
