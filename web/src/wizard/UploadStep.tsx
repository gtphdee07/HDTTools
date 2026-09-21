import { useRef } from 'react';
import { Check, Upload } from 'lucide-react';
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
  const isScale = module.key === 'scale';

  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 40, flexWrap: 'wrap' }}>
      <div style={{ flex: '1 1 480px', minWidth: 320 }}>
        <h1 style={{ fontSize: 'var(--text-h1)', margin: '0 0 10px', color: 'var(--fg-1)' }}>{module.title}</h1>
        <p style={{ color: 'var(--fg-2)', fontSize: 'var(--text-body-lg)', margin: '0 0 20px' }}>{module.instructions}</p>
        {isScale && (
          <p style={{ color: 'var(--fg-2)', fontSize: 13, margin: '-8px 0 20px', fontStyle: 'italic' }}>
            No CAT scale ticket? You can skip this step and still build an estimated model from your truck and
            trailer tag ratings.
          </p>
        )}
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
          style={{
            width: '100%',
            minHeight: 260,
            boxSizing: 'border-box',
            borderRadius: 'var(--radius-lg)',
            border: '2px dashed var(--border-strong)',
            background: 'var(--bg-surface-sunken)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            padding: 24,
            textAlign: 'center',
            marginBottom: 20,
          }}
        >
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 'var(--radius-pill)',
              background: 'var(--color-tint-teal)',
              color: 'var(--accent-secondary-hover)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Upload size={26} />
          </div>
          <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17 }}>
            {file ? `Selected: ${file.name}` : 'Drop a photo here'}
          </div>
          {!file && <div style={{ fontSize: 13, color: 'var(--fg-2)' }}>{module.slotPlaceholder}</div>}
          <Button variant="secondary" size="md" onClick={() => inputRef.current?.click()}>
            Choose photo
          </Button>
        </div>
        {error && (
          <div style={{ color: 'var(--state-danger)', fontSize: 13, marginBottom: 16 }}>{error}</div>
        )}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <Button variant="primary" size="md" onClick={onExtract} disabled={!file}>
            Extract Data
          </Button>
          <Button variant="ghost" size="md" onClick={onSkip}>
            {isScale ? 'No Image / Enter Weight Manually' : "I don't have this image"}
          </Button>
          {isScale && (
            <Button variant="secondary" size="md" onClick={onSkip}>
              Build Estimated Model / No CAT scale info
            </Button>
          )}
        </div>
      </div>

      <div
        style={{
          flex: '0 0 320px',
          boxSizing: 'border-box',
          padding: 28,
          borderRadius: 'var(--radius-lg)',
          background: 'var(--color-tint-teal)',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--accent-secondary-hover)' }}>
          What we read
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {module.fields.map((f) => (
            <div key={f.name} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 15 }}>
              <Check size={18} color="var(--accent-secondary-hover)" />
              {f.label}
            </div>
          ))}
        </div>
        <div style={{ height: 1, background: 'var(--border-subtle)' }} />
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5 }}>
          Glare or a blurry label? You can type the numbers in yourself instead.
        </p>
      </div>
    </div>
  );
}
