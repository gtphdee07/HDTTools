import { AlertTriangle, CheckCircle2, HelpCircle } from 'lucide-react';
import type { BreakdownItem, VerdictInfo } from '../types';
import { Button } from '../design-system/Button';
import { Badge } from '../design-system/Badge';
import { PredictiveEstimateNotice } from '../components/PredictiveEstimateNotice';

interface ResultsStepProps {
  verdict: VerdictInfo;
  breakdownItems: BreakdownItem[];
  onRestart: () => void;
  onGoHome: () => void;
}

const VERDICT_ICONS = { 'alert-triangle': AlertTriangle, 'check-circle-2': CheckCircle2, 'help-circle': HelpCircle };

export function ResultsStep({ verdict, breakdownItems, onRestart, onGoHome }: ResultsStepProps) {
  const Icon = VERDICT_ICONS[verdict.icon];

  return (
    <div>
      <div
        style={{
          background: verdict.bandBg,
          borderRadius: 'var(--radius-lg)',
          padding: '28px 32px',
          display: 'flex',
          alignItems: 'center',
          gap: 20,
          marginBottom: 28,
          boxShadow: 'var(--shadow-md)',
        }}
      >
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.25)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flex: 'none',
          }}
        >
          <Icon size={30} color="#fff" />
        </div>
        <div>
          <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 'var(--text-h2)', color: '#fff' }}>
            {verdict.headline}
          </div>
          <div style={{ color: 'rgba(255,255,255,0.9)', fontSize: 14, marginTop: 4 }}>{verdict.subline}</div>
        </div>
      </div>

      {breakdownItems.some((item) => item.estimated) && <PredictiveEstimateNotice />}

      <h3 style={{ fontSize: 'var(--text-h3)', margin: '0 0 14px' }}>Axle-by-axle breakdown</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 28 }}>
        {breakdownItems.map((item) => (
          <div
            key={item.label}
            style={{
              background: 'var(--surface-card)',
              borderRadius: 'var(--radius-md)',
              boxShadow: 'var(--shadow-sm)',
              padding: '16px 20px',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'baseline',
                marginBottom: 8,
                gap: 12,
              }}
            >
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15 }}>{item.label}</div>
              <Badge tone={item.tone}>{item.badgeLabel}</Badge>
            </div>
            <div
              style={{
                height: 10,
                borderRadius: 'var(--radius-pill)',
                background: 'var(--color-cream-dark)',
                overflow: 'hidden',
                marginBottom: 8,
              }}
            >
              <div
                style={{
                  height: '100%',
                  borderRadius: 'var(--radius-pill)',
                  width: `${item.pct}%`,
                  background: item.barColor,
                }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--fg-2)' }}>
              <span>{item.actualLabel} actual</span>
              <span>{item.limitLabel} rated</span>
            </div>
            {item.note && (
              <div style={{ fontSize: 12, color: 'var(--fg-2)', marginTop: 8, fontStyle: 'italic' }}>{item.note}</div>
            )}
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 12 }}>
        <Button variant="primary" size="md" onClick={onRestart}>
          Run Another Check
        </Button>
        <Button variant="ghost" size="md" onClick={onGoHome}>
          Back to Dashboard
        </Button>
      </div>
    </div>
  );
}
