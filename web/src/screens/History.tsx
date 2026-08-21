import type { HistoryEntry } from '../types';
import { Badge } from '../design-system/Badge';
import { VERDICT_BADGE } from '../verdictBadge';

interface HistoryProps {
  history: HistoryEntry[];
}

export function History({ history }: HistoryProps) {
  return (
    <div>
      <h1 style={{ fontSize: 'var(--text-h1)', margin: '0 0 20px', color: 'var(--fg-1)' }}>Check History</h1>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {history.map((h) => {
          const badge = VERDICT_BADGE[h.verdict];
          return (
            <div
              key={h.id}
              style={{
                background: 'var(--surface-card)',
                borderRadius: 'var(--radius-md)',
                boxShadow: 'var(--shadow-sm)',
                padding: '16px 20px',
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
              <Badge tone={badge.tone}>{badge.label}</Badge>
            </div>
          );
        })}
      </div>
    </div>
  );
}
