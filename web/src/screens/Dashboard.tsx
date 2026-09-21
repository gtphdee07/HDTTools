import { ArrowRight, Plus } from 'lucide-react';
import type { HistoryEntry, RecentRig } from '../types';
import { Button } from '../design-system/Button';
import { Badge } from '../design-system/Badge';
import { VERDICT_BADGE } from '../verdictBadge';

interface DashboardProps {
  recentRigs: RecentRig[];
  history: HistoryEntry[];
  onStartWizard: () => void;
  onGoHistory: () => void;
}

const RIG_DOT_COLORS = ['var(--color-teal)', 'var(--color-purple)', 'var(--accent-primary)'];

export function Dashboard({ recentRigs, history, onStartWizard, onGoHistory }: DashboardProps) {
  const recentHistory = history.slice(0, 2);
  const rigByNickname = new Map(recentRigs.map((rig) => [rig.nickname, rig]));

  return (
    <div>
      {/* Hero */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 48,
          flexWrap: 'wrap',
          padding: '20px 0 48px',
        }}
      >
        <div style={{ maxWidth: 520, display: 'flex', flexDirection: 'column', gap: 20 }}>
          <span
            style={{
              display: 'inline-flex',
              alignSelf: 'flex-start',
              alignItems: 'center',
              padding: '6px 14px',
              borderRadius: 'var(--radius-pill)',
              background: 'var(--color-tint-orange)',
              color: 'var(--color-orange-deep)',
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
            }}
          >
            Free to start
          </span>
          <h1 style={{ fontSize: 'var(--text-display-2)', margin: 0, color: 'var(--fg-1)' }}>
            <span style={{ display: 'block' }}>Weigh in before</span>
            <span style={{ display: 'block', color: 'var(--accent-tertiary)' }}>you hit the road.</span>
          </h1>
          <p style={{ fontSize: 'var(--text-body-lg)', color: 'var(--fg-2)', margin: 0 }}>
            Snap your truck tag, trailer tag, and CAT scale ticket — we'll check every axle against its rating and
            give you a plain-language answer.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
            <Button variant="primary" size="lg" onClick={onStartWizard}>
              Start New Check
            </Button>
            <Button variant="secondary" size="lg" onClick={onGoHistory}>
              View History
            </Button>
          </div>
          <span style={{ fontSize: 13, color: 'var(--fg-2)' }}>Manual entry is always free. Photo scans use credits.</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, width: 340, flexShrink: 0 }}>
          {[
            { n: 1, title: 'Truck tag', body: 'Manufacturer and three weight ratings.', bg: 'var(--color-teal)', fg: 'var(--fg-1)' },
            { n: 2, title: 'Trailer tag', body: 'Its own label, read the same way.', bg: 'var(--color-purple)', fg: '#fff' },
            { n: 3, title: 'Scale ticket', body: 'Your CAT Scale weigh ticket.', bg: 'var(--accent-primary)', fg: 'var(--fg-1)' },
          ].map((step) => (
            <div
              key={step.n}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 16,
                padding: '18px 22px',
                borderRadius: 'var(--radius-lg)',
                background: step.bg,
                color: step.fg,
              }}
            >
              <div
                style={{
                  width: 40,
                  height: 40,
                  flexShrink: 0,
                  borderRadius: 'var(--radius-pill)',
                  background: 'var(--bg-surface)',
                  color: 'var(--fg-1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontFamily: 'var(--font-display)',
                  fontWeight: 800,
                  fontSize: 18,
                }}
              >
                {step.n}
              </div>
              <div>
                <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 17 }}>{step.title}</div>
                <div style={{ fontSize: 13.5, lineHeight: 1.4 }}>{step.body}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent checks */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '24px 0 16px' }}>
        <h2 style={{ fontSize: 'var(--text-h1)', color: 'var(--fg-1)', margin: 0 }}>Recent Checks</h2>
        {history.length > 0 && (
          <button
            onClick={onGoHistory}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: 0,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              color: 'var(--accent-secondary-hover)',
              fontWeight: 700,
              fontSize: 14,
            }}
          >
            View history <ArrowRight size={16} />
          </button>
        )}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 18, marginBottom: 40 }}>
        {recentHistory.map((h) => {
          const rig = rigByNickname.get(h.rigNickname);
          const subtitle = rig ? [rig.truck.manufacturer, rig.trailer.manufacturer].filter(Boolean).join(' + ') : undefined;
          const badge = VERDICT_BADGE[h.verdict];
          return (
            <div
              key={h.id}
              style={{
                background: 'var(--surface-card)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-sm)',
                padding: 24,
                display: 'flex',
                flexDirection: 'column',
                gap: 12,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                <div>
                  <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17 }}>{h.rigNickname}</div>
                  <div style={{ fontSize: 13, color: 'var(--fg-2)' }}>
                    {h.date}
                    {subtitle ? ` · ${subtitle}` : ''}
                  </div>
                </div>
                <Badge tone={badge.tone}>{badge.label}</Badge>
              </div>
            </div>
          );
        })}
        {recentHistory.length === 0 && (
          <div style={{ color: 'var(--fg-2)', fontSize: 14 }}>No checks yet — run your first one above.</div>
        )}
      </div>

      {/* Your rigs */}
      <h2 style={{ fontSize: 'var(--text-h1)', color: 'var(--fg-1)', margin: '0 0 16px' }}>Your Rigs</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 18 }}>
        {recentRigs.map((rig, i) => {
          const truckLabel = rig.truck.manufacturer;
          const trailerLabel = rig.trailer.manufacturer;
          return (
            <div
              key={rig.nickname}
              onClick={onStartWizard}
              style={{
                display: 'flex',
                flexDirection: 'column',
                height: 180,
                boxSizing: 'border-box',
                padding: 20,
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                background: 'var(--surface-card)',
                boxShadow: 'var(--shadow-sm)',
                cursor: 'pointer',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: '0.04em',
                  textTransform: 'uppercase',
                  color: 'var(--fg-2)',
                }}
              >
                <span
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: 'var(--radius-pill)',
                    background: RIG_DOT_COLORS[i % RIG_DOT_COLORS.length],
                  }}
                />
                Rig
              </div>
              <div style={{ marginTop: 10, fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17 }}>
                {rig.nickname}
              </div>
              {truckLabel && <div style={{ fontSize: 13, color: 'var(--fg-2)' }}>Truck: {truckLabel}</div>}
              {trailerLabel && <div style={{ fontSize: 13, color: 'var(--fg-2)' }}>Trailer: {trailerLabel}</div>}
              <div
                style={{
                  marginTop: 'auto',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  fontWeight: 700,
                  fontSize: 14,
                  color: 'var(--accent-secondary-hover)',
                }}
              >
                Start check <ArrowRight size={16} />
              </div>
            </div>
          );
        })}
        <div
          onClick={onStartWizard}
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 10,
            height: 180,
            boxSizing: 'border-box',
            padding: 20,
            border: '2px dashed var(--border-strong)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--fg-1)',
            cursor: 'pointer',
          }}
        >
          <span
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 40,
              height: 40,
              borderRadius: 'var(--radius-pill)',
              background: 'var(--color-teal)',
              color: 'var(--fg-1)',
            }}
          >
            <Plus size={20} />
          </span>
          <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16 }}>New rig</span>
          <span style={{ fontSize: 13, color: 'var(--fg-2)' }}>Start with a nickname</span>
        </div>
      </div>

      {/* Upgrade teaser - static/inert: no Paywall exists yet (item #20) */}
      <div
        style={{
          marginTop: 48,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 40,
          flexWrap: 'wrap',
          padding: '40px 44px',
          borderRadius: 'var(--radius-lg)',
          background: 'var(--accent-tertiary)',
          color: '#fff',
        }}
      >
        <div style={{ maxWidth: 480, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            Scanning credits
          </span>
          <h2 style={{ fontSize: 'var(--text-h2)', margin: 0, color: '#fff' }}>Tricky label? Let Claude read it.</h2>
          <p style={{ margin: 0, fontSize: 15, lineHeight: 1.5 }}>
            Photo scans use credits. Manual entry is always free. Coming soon.
          </p>
        </div>
        <Button variant="primary" size="lg" disabled>
          See credit packs
        </Button>
      </div>
    </div>
  );
}
