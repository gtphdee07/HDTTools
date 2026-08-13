import type { ReactNode } from 'react';

type Tone = 'success' | 'warning' | 'neutral';

interface BadgeProps {
  tone: Tone;
  children: ReactNode;
}

const toneStyles: Record<Tone, React.CSSProperties> = {
  success: { background: 'color-mix(in oklch, var(--color-trail-green) 18%, white)', color: 'var(--color-trail-green-dark)' },
  warning: { background: 'color-mix(in oklch, var(--color-sunset-orange) 20%, white)', color: 'var(--color-sunset-orange-dark)' },
  neutral: { background: 'var(--color-cream-dark)', color: 'var(--fg-2)' },
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
