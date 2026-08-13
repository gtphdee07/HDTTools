import { Button } from '../design-system/Button';

interface DisclaimerModalProps {
  onAcknowledge: () => void;
}

export function DisclaimerModal({ onAcknowledge }: DisclaimerModalProps) {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(42, 42, 40, 0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        zIndex: 1000,
      }}
    >
      <div
        style={{
          background: 'var(--surface-card)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-lg)',
          padding: 32,
          maxWidth: 520,
        }}
      >
        <h2 style={{ fontSize: 'var(--text-h2)', margin: '0 0 14px' }}>
          ⚠️ Experimental Tool — Not for Safety Decisions
        </h2>
        <p style={{ color: 'var(--fg-2)', fontSize: 14, lineHeight: 'var(--leading-normal)', margin: '0 0 14px' }}>
          RigCheck is an experimental project built to learn AI-assisted software development, not a
          certified or professional weight-safety tool. Its numbers come from OCR-read photos,
          manually reviewed by you, and simplified math — any step of that chain can be wrong.
        </p>
        <p style={{ color: 'var(--fg-2)', fontSize: 14, lineHeight: 'var(--leading-normal)', margin: '0 0 24px' }}>
          Do not use this tool to decide whether your rig is safe to tow. Always verify actual
          weights and ratings using a certified scale and your vehicle's official documentation, and
          consult a qualified professional if you're unsure. You use this tool, and any decisions you
          make based on it, entirely at your own risk and responsibility.
        </p>
        <Button variant="primary" size="md" onClick={onAcknowledge}>
          I Understand — Continue
        </Button>
      </div>
    </div>
  );
}
