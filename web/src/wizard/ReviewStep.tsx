import type { ModuleDef } from '../mockData';
import { Button } from '../design-system/Button';

interface ReviewStepProps {
  module: ModuleDef;
  data: Record<string, unknown>;
  onFieldChange: (name: string, isNumber: boolean, value: string) => void;
  onContinue: () => void;
}

export function ReviewStep({ module, data, onFieldChange, onContinue }: ReviewStepProps) {
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
      <h2 style={{ fontSize: 'var(--text-h2)', margin: '0 0 6px' }}>Check the numbers</h2>
      <p style={{ color: 'var(--fg-2)', fontSize: 14, margin: '0 0 20px' }}>
        Here's what we read off your photo. Fix anything that looks off.
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 24 }}>
        {module.fields.map((f) => {
          const raw = data[f.name];
          const value = raw == null ? '' : String(raw);
          return (
            <label key={f.name} style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg-2)' }}>{f.label}</span>
              <input
                type={f.type}
                value={value}
                onChange={(e) => onFieldChange(f.name, f.type === 'number', e.target.value)}
              />
            </label>
          );
        })}
      </div>
      <Button variant="primary" size="md" onClick={onContinue}>
        {module.continueLabel}
      </Button>
    </div>
  );
}
