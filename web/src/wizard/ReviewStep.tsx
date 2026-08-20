import { useRef, useState } from 'react';
import type { ModuleDef } from '../mockData';
import { Button } from '../design-system/Button';

interface ReviewStepProps {
  module: ModuleDef;
  data: Record<string, unknown>;
  error: string | null;
  onFieldChange: (name: string, isNumber: boolean, value: string) => void;
  onContinue: () => void;
  // Truck-step-only extras (per the "fold it into the Truck Tag step"
  // decision, rather than a new wizard step) - undefined on the other
  // two modules, where this section just doesn't render.
  pinWeightPct?: number;
  onPinWeightPctChange?: (value: number) => void;
  onScanStandaloneTicket?: (file: File) => Promise<void>;
}

export function ReviewStep({
  module,
  data,
  error,
  onFieldChange,
  onContinue,
  pinWeightPct,
  onPinWeightPctChange,
  onScanStandaloneTicket,
}: ReviewStepProps) {
  const standaloneInputRef = useRef<HTMLInputElement>(null);
  const [scanningStandalone, setScanningStandalone] = useState(false);
  const [standaloneScanError, setStandaloneScanError] = useState<string | null>(null);

  const showStandaloneTicketScan = module.key === 'truck' && onScanStandaloneTicket;
  const standaloneWeightKnown = Boolean(data.standalone_weight_lb);

  const handleStandaloneFile = async (file: File) => {
    if (!onScanStandaloneTicket) return;
    setScanningStandalone(true);
    setStandaloneScanError(null);
    try {
      await onScanStandaloneTicket(file);
    } catch (err) {
      setStandaloneScanError(err instanceof Error ? err.message : 'Could not read that photo — try again.');
    } finally {
      setScanningStandalone(false);
    }
  };

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

      {showStandaloneTicketScan && (
        <div
          style={{
            background: 'var(--bg-surface-sunken)',
            borderRadius: 'var(--radius-md)',
            padding: 16,
            marginBottom: 24,
          }}
        >
          <p style={{ fontSize: 13, fontWeight: 600, margin: '0 0 4px' }}>
            Don't know your tow vehicle's stand-alone weight?
          </p>
          <p style={{ fontSize: 13, color: 'var(--fg-2)', margin: '0 0 12px' }}>
            Scan a CAT Scale ticket weighing just your tow vehicle (no trailer
            attached) and we'll fill in the field above for you.
          </p>
          <input
            ref={standaloneInputRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={(e) => {
              const picked = e.target.files?.[0];
              if (picked) void handleStandaloneFile(picked);
            }}
          />
          <Button
            variant="secondary"
            size="sm"
            onClick={() => standaloneInputRef.current?.click()}
            disabled={scanningStandalone}
          >
            {scanningStandalone ? 'Reading…' : 'Scan tow-vehicle-only ticket'}
          </Button>
          {standaloneScanError && (
            <div style={{ color: 'var(--state-danger)', fontSize: 12, marginTop: 8 }}>{standaloneScanError}</div>
          )}

          {!standaloneWeightKnown && pinWeightPct !== undefined && onPinWeightPctChange && (
            <div style={{ marginTop: 16 }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg-2)' }}>
                  No ticket? Estimate pin/hitch weight as {pinWeightPct}% of the trailer's weight
                </span>
                <input
                  type="range"
                  min={15}
                  max={25}
                  step={1}
                  value={pinWeightPct}
                  onChange={(e) => onPinWeightPctChange(Number(e.target.value))}
                />
              </label>
              <p style={{ fontSize: 12, color: 'var(--fg-2)', margin: '4px 0 0' }}>
                Industry recommendations are typically 15-25% — we default to 20%.
              </p>
            </div>
          )}
        </div>
      )}

      {error && (
        <div style={{ color: 'var(--state-danger)', fontSize: 13, marginBottom: 16 }}>{error}</div>
      )}
      <Button variant="primary" size="md" onClick={onContinue}>
        {module.continueLabel}
      </Button>
    </div>
  );
}
