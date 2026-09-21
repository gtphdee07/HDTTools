import { useMemo, useState } from 'react';
import { ArrowRight } from 'lucide-react';
import type { HistoryEntry, RecentRig } from '../types';
import { Badge } from '../design-system/Badge';
import { VERDICT_BADGE } from '../verdictBadge';

interface HistoryProps {
  history: HistoryEntry[];
  recentRigs?: RecentRig[];
}

type Filter = 'all' | 'within' | 'over' | `rig:${string}`;

export function History({ history, recentRigs = [] }: HistoryProps) {
  const [filter, setFilter] = useState<Filter>('all');
  const rigByNickname = new Map(recentRigs.map((rig) => [rig.nickname, rig]));
  const rigNicknames = useMemo(
    () => Array.from(new Set(history.map((h) => h.rigNickname))),
    [history],
  );

  const filtered = history.filter((h) => {
    if (filter === 'all') return true;
    if (filter === 'within') return h.verdict === 'pass';
    if (filter === 'over') return h.verdict === 'fail';
    return h.rigNickname === filter.slice(4);
  });

  const pillStyle = (active: boolean): React.CSSProperties => ({
    display: 'inline-flex',
    alignItems: 'center',
    height: 40,
    boxSizing: 'border-box',
    padding: '0 18px',
    borderRadius: 'var(--radius-pill)',
    background: active ? 'var(--accent-tertiary)' : 'var(--bg-surface)',
    border: active ? 'none' : '2px solid var(--border-strong)',
    color: active ? '#fff' : 'var(--fg-1)',
    fontWeight: 700,
    fontSize: 14,
    cursor: 'pointer',
  });

  return (
    <div>
      <h1 style={{ fontSize: 'var(--text-h1)', margin: '0 0 6px', color: 'var(--fg-1)' }}>Check History</h1>
      <p style={{ fontSize: 'var(--text-body-lg)', color: 'var(--fg-2)', margin: '0 0 24px' }}>
        Every check you have run and where you stood.
      </p>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 20 }}>
        <button style={pillStyle(filter === 'all')} onClick={() => setFilter('all')}>
          All rigs
        </button>
        {rigNicknames.map((nickname) => (
          <button key={nickname} style={pillStyle(filter === `rig:${nickname}`)} onClick={() => setFilter(`rig:${nickname}`)}>
            {nickname}
          </button>
        ))}
        <button style={pillStyle(filter === 'within')} onClick={() => setFilter('within')}>
          Within limits
        </button>
        <button style={pillStyle(filter === 'over')} onClick={() => setFilter('over')}>
          Over limit
        </button>
      </div>

      <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)', overflow: 'hidden', background: 'var(--surface-card)', boxShadow: 'var(--shadow-sm)' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '140px minmax(0, 1fr) minmax(0, 1fr) 180px 80px',
            columnGap: 16,
            alignItems: 'center',
            padding: '12px 24px',
            background: 'var(--bg-surface-sunken)',
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            color: 'var(--fg-2)',
          }}
        >
          <div>Date</div>
          <div>Rig</div>
          <div>Truck and trailer</div>
          <div>Verdict</div>
          <div />
        </div>
        {filtered.map((h, i) => {
          const badge = VERDICT_BADGE[h.verdict];
          const rig = rigByNickname.get(h.rigNickname);
          const subtitle = rig ? [rig.truck.manufacturer, rig.trailer.manufacturer].filter(Boolean).join(' + ') : '—';
          return (
            <div
              key={h.id}
              style={{
                display: 'grid',
                gridTemplateColumns: '140px minmax(0, 1fr) minmax(0, 1fr) 180px 80px',
                columnGap: 16,
                alignItems: 'center',
                padding: '16px 24px',
                borderTop: i > 0 ? '1px solid var(--border-subtle)' : 'none',
              }}
            >
              <div style={{ fontSize: 14 }}>{h.date}</div>
              <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15 }}>{h.rigNickname}</div>
              <div style={{ fontSize: 13, color: 'var(--fg-2)' }}>{subtitle}</div>
              <div>
                <Badge tone={badge.tone}>{badge.label}</Badge>
              </div>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--accent-secondary-hover)', fontWeight: 700, fontSize: 13 }}>
                View <ArrowRight size={14} />
              </div>
            </div>
          );
        })}
        {filtered.length === 0 && (
          <div style={{ padding: '32px 24px', color: 'var(--fg-2)', fontSize: 14 }}>No checks match this filter.</div>
        )}
      </div>
    </div>
  );
}
