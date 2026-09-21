import { Check } from 'lucide-react';

interface ProcessingStepProps {
  title: string;
}

const CHECKLIST = ['Photo received', 'Reading the label', 'Checking the numbers'];

export function ProcessingStep({ title }: ProcessingStepProps) {
  return (
    <div
      style={{
        maxWidth: 640,
        margin: '0 auto',
        boxSizing: 'border-box',
        padding: '48px 40px',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
        background: 'var(--surface-card)',
        boxShadow: 'var(--shadow-sm)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 12,
        textAlign: 'center',
      }}
    >
      <svg width="88" height="88" viewBox="0 0 96 96" role="img" aria-label="Reading in progress">
        <circle cx="48" cy="48" r="40" fill="none" stroke="var(--bg-surface-sunken)" strokeWidth="8" />
        <circle
          cx="48"
          cy="48"
          r="40"
          fill="none"
          stroke="var(--accent-tertiary)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray="80 172"
          transform="rotate(-90 48 48)"
          style={{ animation: 'spin 1.4s linear infinite', transformOrigin: '48px 48px' }}
        />
      </svg>
      <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 'var(--text-h1)', color: 'var(--fg-1)', marginTop: 8 }}>
        Reading {title}&hellip;
      </div>
      <p style={{ margin: 0, fontSize: 15, color: 'var(--fg-2)' }}>Hang tight while we read the label.</p>

      <div style={{ marginTop: 12, width: '100%', maxWidth: 360, display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'flex-start' }}>
        {CHECKLIST.map((step, i) => {
          const done = i === 0;
          const current = i === 1;
          return (
            <div key={step} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {done ? (
                <span
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: 'var(--radius-pill)',
                    background: 'var(--accent-secondary-hover)',
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <Check size={14} />
                </span>
              ) : (
                <span
                  style={{
                    width: 24,
                    height: 24,
                    boxSizing: 'border-box',
                    borderRadius: 'var(--radius-pill)',
                    border: current ? '4px solid var(--accent-tertiary)' : '2px solid var(--border-strong)',
                    background: 'var(--bg-surface)',
                    flexShrink: 0,
                  }}
                />
              )}
              <span style={{ fontSize: 15, fontWeight: current ? 700 : 400, color: current ? 'var(--fg-1)' : 'var(--fg-2)' }}>
                {step}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
