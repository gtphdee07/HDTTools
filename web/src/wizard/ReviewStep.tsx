import { useRef, useState } from 'react';
import type { ModuleDef } from '../mockData';
import { Button } from '../design-system/Button';
import { ScanGate } from '../components/ScanGate';
import { ScanError } from '../scanError';
import type { ScanAccess } from '../scanAccess';
import { scanNoticeText } from '../scanNotice';
import type { ScanNotice } from '../scanNotice';

interface ReviewStepProps {
  module: ModuleDef;
  data: Record<string, unknown>;
  error: string | null;
  // Set when this step was reached from a Scan that did not fill every field; left out otherwise.
  scanNotice?: ScanNotice | null;
  // Offered with the notice for a Scan that read nothing: back to the photo step, without sending anything.
  onChooseDifferentPhoto?: () => void;
  onFieldChange: (name: string, isNumber: boolean, value: string) => void;
  onContinue: () => void;
  // Truck-step-only extras (per the "fold it into the Truck Tag step"
  // decision, rather than a new wizard step) - undefined on the other
  // two modules, where this section just doesn't render.
  pinWeightPct?: number;
  onPinWeightPctChange?: (value: number) => void;
  onScanStandaloneTicket?: (file: File) => Promise<void>;
  // Whether this visitor can scan that ticket; when not, the way past it is shown in place of the button.
  // Left out, the ticket scan is offered unconditionally.
  scanAccess?: ScanAccess;
  onGoAccount?: () => void;
  onRetryScanAccess?: () => void;
}

export function ReviewStep({
  module,
  data,
  error,
  scanNotice,
  onChooseDifferentPhoto,
  onFieldChange,
  onContinue,
  pinWeightPct,
  onPinWeightPctChange,
  onScanStandaloneTicket,
  scanAccess,
  onGoAccount,
  onRetryScanAccess,
}: ReviewStepProps) {
  const standaloneInputRef = useRef<HTMLInputElement>(null);
  const [scanningStandalone, setScanningStandalone] = useState(false);
  const [standaloneScanError, setStandaloneScanError] = useState<string | null>(null);
  // The photo of a ticket scan that did not deliver, kept so "Try again" re-runs it with the same File
  // (and so the same request id: a retry after a lost response is then charged once).
  const [failedTicket, setFailedTicket] = useState<File | null>(null);
  // Whether sending that same photo again could help. When it cannot (a delivered answer with no weight in it,
  // a refusal that repeats, a photo that cannot be sent), the next step is a different photo instead.
  const [retryHelps, setRetryHelps] = useState(true);
  // The failure was a delivered, charged Scan with no weight in it: typing the weight in is then the other way on.
  const [noWeight, setNoWeight] = useState(false);
  const standaloneWeightRef = useRef<HTMLInputElement>(null);

  // Warn only: a GCWR under the GVWR is unusual but still used (the owner's manual may be right and the tag wrong).
  // Needs a known GVWR to compare against; a blank or 0 field means "not entered".
  const gcwr = typeof data.gcwr_lb === 'number' ? data.gcwr_lb : 0;
  const gvwr = typeof data.gvwr_lb === 'number' ? data.gvwr_lb : 0;
  const gcwrBelowGvwr = module.key === 'truck' && gcwr > 0 && gvwr > 0 && gcwr < gvwr;

  const showStandaloneTicketScan = module.key === 'truck' && onScanStandaloneTicket;
  const standaloneWeightKnown = Boolean(data.standalone_weight_lb);
  const canScanTicket = !scanAccess || scanAccess.kind === 'ready';
  // A refused account token blocks scanning until the user signs in again, but a different photo is still
  // offered after it (it is the photo they will use once they are back); typing the weight in never needs a scan.
  const canPickAnother = canScanTicket || scanAccess?.kind === 'sign-in-again';
  const showTryAgain = failedTicket && !scanningStandalone && canScanTicket && retryHelps;
  const showDifferentPhoto = failedTicket && !scanningStandalone && canPickAnother && !retryHelps;
  const showTypeItIn = failedTicket && !scanningStandalone && noWeight;

  const handleStandaloneFile = async (file: File) => {
    if (!onScanStandaloneTicket) return;
    setScanningStandalone(true);
    setStandaloneScanError(null);
    setFailedTicket(null);
    setRetryHelps(true);
    setNoWeight(false);
    try {
      await onScanStandaloneTicket(file);
    } catch (err) {
      setFailedTicket(file);
      setRetryHelps(!(err instanceof ScanError) || err.canTryAgain);
      setNoWeight(err instanceof ScanError && err.code === 'no_weight');
      setStandaloneScanError(err instanceof Error ? err.message : 'Could not read that photo — try again.');
    } finally {
      setScanningStandalone(false);
    }
  };

  return (
    <div style={{ maxWidth: 620, margin: '0 auto' }}>
      <h1 style={{ fontSize: 'var(--text-h1)', margin: '0 0 10px', color: 'var(--fg-1)' }}>Check the numbers</h1>
      <p style={{ color: 'var(--fg-2)', fontSize: 'var(--text-body-lg)', margin: '0 0 24px' }}>
        Here's what we read off your photo. Fix anything that looks off before we do the math.
      </p>
      {scanNotice && (
        <div
          style={{
            background: 'var(--color-tint-purple)',
            color: 'var(--fg-1)',
            borderRadius: 12,
            padding: '12px 16px',
            marginBottom: 24,
            fontSize: 14,
          }}
        >
          <p style={{ margin: 0 }}>{scanNoticeText(scanNotice)}</p>
          {scanNotice.kind === 'nothing-read' && onChooseDifferentPhoto && (
            <div style={{ marginTop: 10 }}>
              <Button variant="secondary" size="sm" onClick={onChooseDifferentPhoto}>
                Choose a different photo
              </Button>
            </div>
          )}
        </div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 18, marginBottom: 24 }}>
        {module.fields.map((f) => {
          const raw = data[f.name];
          const value = raw == null ? '' : String(raw);
          const hintId = f.hint ? `hint-${f.name}` : undefined;
          return (
            <div key={f.name} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--fg-1)' }}>{f.label}</span>
                <input
                  ref={f.name === 'standalone_weight_lb' ? standaloneWeightRef : undefined}
                  type={f.type}
                  value={value}
                  aria-describedby={hintId}
                  onChange={(e) => onFieldChange(f.name, f.type === 'number', e.target.value)}
                />
              </label>
              {f.hint && (
                <span id={hintId} style={{ fontSize: 12, color: 'var(--fg-2)' }}>
                  {f.hint}
                </span>
              )}
              {f.name === 'gcwr_lb' && gcwrBelowGvwr && (
                <span role="alert" style={{ fontSize: 13, color: 'var(--state-danger)' }}>
                  That GCWR ({gcwr.toLocaleString('en-US')} lb) is below the truck's GVWR ({gvwr.toLocaleString('en-US')}{' '}
                  lb), which is unusual. Double-check it against your owner's manual. We'll still use it.
                </span>
              )}
            </div>
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
          {scanAccess && onGoAccount && onRetryScanAccess && (
            <ScanGate access={scanAccess} onGoAccount={onGoAccount} onRetry={onRetryScanAccess} />
          )}
          <input
            ref={standaloneInputRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={(e) => {
              const picked = e.target.files?.[0];
              // Reset so picking the same photo again still fires a change.
              e.target.value = '';
              if (picked) void handleStandaloneFile(picked);
            }}
          />
          {canScanTicket && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => standaloneInputRef.current?.click()}
              disabled={scanningStandalone}
            >
              {scanningStandalone ? 'Reading…' : 'Scan tow-vehicle-only ticket'}
            </Button>
          )}
          {standaloneScanError && (
            <div style={{ color: 'var(--state-danger)', fontSize: 12, marginTop: 8 }}>{standaloneScanError}</div>
          )}
          {(showTryAgain || showDifferentPhoto || showTypeItIn) && (
            <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {showTryAgain && (
                <Button variant="secondary" size="sm" onClick={() => failedTicket && void handleStandaloneFile(failedTicket)}>
                  Try again
                </Button>
              )}
              {showDifferentPhoto && (
                <Button variant="secondary" size="sm" onClick={() => standaloneInputRef.current?.click()}>
                  Choose a different photo
                </Button>
              )}
              {showTypeItIn && (
                <Button variant="ghost" size="sm" onClick={() => standaloneWeightRef.current?.focus()}>
                  Type it in
                </Button>
              )}
            </div>
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
