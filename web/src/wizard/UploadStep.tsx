import { useRef } from 'react';
import type { ModuleDef } from '../mockData';
import { Button } from '../design-system/Button';

interface UploadStepProps {
  module: ModuleDef;
  file: File | null;
  error: string | null;
  onFileSelected: (file: File) => void;
  onExtract: () => void;
  onSkip: () => void;
}

export function UploadStep({ module, file, error, onFileSelected, onExtract, onSkip }: UploadStepProps) {
  const inputRef = useRef<HTMLInputElement>(null);

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
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={(e) => {
          const picked = e.target.files?.[0];
          if (picked) onFileSelected(picked);
        }}
      />
      <div
        onClick={() => inputRef.current?.click()}
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
          cursor: 'pointer',
        }}
      >
        {file ? `Selected: ${file.name}` : module.slotPlaceholder}
      </div>
      {error && (
        <div style={{ color: 'var(--state-danger)', fontSize: 13, marginBottom: 16 }}>{error}</div>
      )}
      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <Button variant="primary" size="md" onClick={onExtract} disabled={!file}>
          Extract Data
        </Button>
        <Button variant="ghost" size="md" onClick={onSkip}>
          I don't have this image
        </Button>
      </div>
    </div>
  );
}
