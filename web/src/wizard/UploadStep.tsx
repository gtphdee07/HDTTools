import type { ModuleDef } from '../mockData';
import { Button } from '../design-system/Button';

interface UploadStepProps {
  module: ModuleDef;
  onExtract: () => void;
}

export function UploadStep({ module, onExtract }: UploadStepProps) {
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
      <h2 style={{ fontSize: 'var(--text-h2)', margin: '0 0 6px' }}>{module.title}</h2>
      <p style={{ color: 'var(--fg-2)', fontSize: 14, margin: '0 0 20px' }}>{module.instructions}</p>
      <div
        style={{
          width: '100%',
          height: 280,
          marginBottom: 20,
          borderRadius: 14,
          border: '2px dashed var(--border-subtle)',
          background: 'var(--bg-surface-sunken)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--fg-2)',
          fontSize: 14,
          textAlign: 'center',
          padding: 16,
        }}
      >
        {module.slotPlaceholder}
      </div>
      <Button variant="primary" size="md" onClick={onExtract}>
        Extract Data
      </Button>
    </div>
  );
}
