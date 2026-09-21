import type { ReactNode } from 'react';

type Tone = 'success' | 'warning' | 'neutral' | 'insufficient';

interface BadgeProps {
  tone: Tone;
  children: ReactNode;
}

const toneStyles: Record<Tone, React.CSSProperties> = {
  success: { background: 'color-mix(in oklch, var(--color-pine) 18%, white)', color: 'var(--color-pine)' },
  warning: { background: 'color-mix(in oklch, var(--color-orange) 20%, white)', color: 'var(--color-orange-deep)' },
  neutral: { background: 'var(--color-surface-sunken)', color: 'var(--fg-2)' },
  // Matches the backend's --state-info color used for "insufficient" rows'
  // barColor - a row we can't check yet, not a pass or a fail.
  insufficient: { background: 'color-mix(in oklch, var(--color-purple) 18%, white)', color: 'var(--color-purple-deep)' },
};

export function Badge({ tone, children }: BadgeProps) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '4px 12px',
        borderRadius: 'var(--radius-pill)',
        fontFamily: 'var(--font-display)',
        fontWeight: 700,
        fontSize: 12,
        whiteSpace: 'nowrap',
        ...toneStyles[tone],
      }}
    >
      {children}
    </span>
  );
}
