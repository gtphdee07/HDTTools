import type { HistoryEntry } from '../types';
import { Badge } from '../design-system/Badge';

interface HistoryProps {
  history: HistoryEntry[];
}

export function History({ history }: HistoryProps) {
  return (
    <div>
      <h1 style={{ fontSize: 'var(--text-h1)', margin: '0 0 20px', color: 'var(--fg-1)' }}>Check History</h1>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {history.map((h) => (
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
                {h.truckName} + {h.trailerName}
              </div>
              <div style={{ fontSize: 13, color: 'var(--fg-2)' }}>{h.date}</div>
            </div>
            <Badge tone={h.verdict === 'pass' ? 'success' : 'warning'}>
              {h.verdict === 'pass' ? 'Safe to Tow' : 'Over Limit'}
            </Badge>
          </div>
        ))}
      </div>
    </div>
  );
}
