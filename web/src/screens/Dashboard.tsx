import type { HistoryEntry, RecentRig } from '../types';
import { Button } from '../design-system/Button';
import { Card } from '../design-system/Card';
import { Badge } from '../design-system/Badge';
import { VERDICT_BADGE } from '../verdictBadge';

interface DashboardProps {
  recentRigs: RecentRig[];
  history: HistoryEntry[];
  onStartWizard: () => void;
}

export function Dashboard({ recentRigs, history, onStartWizard }: DashboardProps) {
  const recentHistory = history.slice(0, 2);

  return (
    <div>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          gap: 16,
          marginBottom: 22,
          flexWrap: 'wrap',
        }}
      >
        <div>
          <h1 style={{ fontSize: 'var(--text-h1)', margin: '0 0 6px', color: 'var(--fg-1)' }}>
            Is your rig safe to roll today?
          </h1>
          <p style={{ fontSize: 'var(--text-body-lg)', color: 'var(--fg-2)', margin: 0, maxWidth: 640 }}>
            Snap your truck tag, trailer tag, and CAT scale ticket — we'll check every axle against its rating and
            give you a plain-language answer.
          </p>
        </div>
        <Button variant="primary" size="lg" onClick={onStartWizard}>
          Start New Check
        </Button>
      </div>

      <h2 style={{ fontSize: 'var(--text-h3)', color: 'var(--fg-1)', margin: '36px 0 14px' }}>Your Recent Rigs</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 18 }}>
        {recentRigs.map((rig) => {
          const subtitle = [rig.truck.manufacturer, rig.trailer.manufacturer].filter(Boolean).join(' + ');
          return (
            <Card key={rig.nickname} title={rig.nickname} subtitle={subtitle || undefined}>
              <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
                <Button variant="secondary" size="sm" onClick={onStartWizard}>
                  Run Check
                </Button>
              </div>
            </Card>
          );
        })}
        <div
          style={{
            border: '2px dashed var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: 120,
            color: 'var(--fg-2)',
            fontSize: 14,
            cursor: 'pointer',
          }}
          onClick={onStartWizard}
        >
          + Add a new rig
        </div>
      </div>

      <h2 style={{ fontSize: 'var(--text-h3)', color: 'var(--fg-1)', margin: '36px 0 14px' }}>Recent Checks</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {recentHistory.map((h) => (
          <div
            key={h.id}
            style={{
              background: 'var(--surface-card)',
              borderRadius: 'var(--radius-md)',
              boxShadow: 'var(--shadow-sm)',
              padding: '14px 20px',
              display: 'flex',
              alignItems: 'center',
              gap: 16,
            }}
          >
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15 }}>
                {h.rigNickname}
              </div>
              <div style={{ fontSize: 13, color: 'var(--fg-2)' }}>{h.date}</div>
            </div>
            <Badge tone={VERDICT_BADGE[h.verdict].tone}>{VERDICT_BADGE[h.verdict].label}</Badge>
          </div>
        ))}
      </div>
    </div>
  );
}
