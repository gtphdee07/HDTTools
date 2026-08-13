import type { ReactNode } from 'react';

interface CardProps {
  title: string;
  subtitle?: string;
  children?: ReactNode;
}

export function Card({ title, subtitle, children }: CardProps) {
  return (
    <div
      style={{
        background: 'var(--surface-card)',
        borderRadius: 'var(--radius-md)',
        boxShadow: 'var(--shadow-sm)',
        padding: '18px 20px',
      }}
    >
      <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15 }}>{title}</div>
      {subtitle && <div style={{ fontSize: 13, color: 'var(--fg-2)', marginTop: 2 }}>{subtitle}</div>}
      {children}
    </div>
  );
}
