import type { ButtonHTMLAttributes } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const sizeStyles: Record<Size, React.CSSProperties> = {
  sm: { padding: '8px 16px', fontSize: 13 },
  md: { padding: '11px 22px', fontSize: 14 },
  lg: { padding: '14px 28px', fontSize: 16 },
};

const variantStyles: Record<Variant, React.CSSProperties> = {
  primary: {
    background: 'var(--accent-primary)',
    color: '#fff',
    border: '1.5px solid transparent',
  },
  secondary: {
    background: 'var(--bg-surface)',
    color: 'var(--accent-secondary-hover)',
    border: '1.5px solid var(--accent-secondary)',
  },
  ghost: {
    background: 'transparent',
    color: 'var(--fg-2)',
    border: '1.5px solid transparent',
  },
};

export function Button({ variant = 'primary', size = 'md', style, ...rest }: ButtonProps) {
  return (
    <button
      {...rest}
      style={{
        fontFamily: 'var(--font-display)',
        fontWeight: 600,
        borderRadius: 'var(--radius-pill)',
        cursor: 'pointer',
        transition: 'opacity 0.15s ease',
        ...sizeStyles[size],
        ...variantStyles[variant],
        ...style,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.opacity = '0.85';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.opacity = '1';
      }}
    />
  );
}
