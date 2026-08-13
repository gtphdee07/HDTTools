interface ProcessingStepProps {
  title: string;
}

export function ProcessingStep({ title }: ProcessingStepProps) {
  return (
    <div
      style={{
        background: 'var(--surface-card)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-md)',
        padding: '60px 32px',
        maxWidth: 560,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 16,
      }}
    >
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: '50%',
          border: '4px solid var(--color-cream-dark)',
          borderTopColor: 'var(--accent-primary)',
          animation: 'spin 0.9s linear infinite',
        }}
      />
      <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, color: 'var(--fg-2)' }}>
        Reading {title}&hellip;
      </div>
    </div>
  );
}
