import type { CSSProperties } from 'react';
import type { ImportResult, RigImport } from '../garageImport';

const banner: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 12,
  background: 'var(--color-tint-purple)',
  color: 'var(--fg-1)',
  borderRadius: 12,
  padding: '12px 16px',
  marginBottom: 20,
  fontSize: 14,
};
const link: CSSProperties = { background: 'none', border: 'none', color: 'var(--fg-2)', cursor: 'pointer', fontSize: 13 };
const action: CSSProperties = { ...link, color: 'var(--fg-1)', fontWeight: 700 };

const rigs = (n: number) => `${n} Rig${n === 1 ? '' : 's'}`;

function resultText(r: ImportResult): string {
  const parts: string[] = [];
  if (r.imported.length > 0) parts.push(`Imported ${rigs(r.imported.length)} to your Garage.`);
  if (r.alreadyThere.length > 0) {
    parts.push(`Already in your Garage under the same nickname, so left as they are: ${r.alreadyThere.join(', ')}.`);
  }
  if (r.notFit.length > 0) {
    const limit = r.cap === null ? 'is full' : `is full (the Free plan holds ${rigs(r.cap)})`;
    parts.push(`Your Garage ${limit}, so these were not imported: ${r.notFit.join(', ')}. They are still saved in this browser.`);
  }
  return parts.join(' ');
}

// Offers Rigs saved in this browser before signing in to the account's Garage, then reports how it went.
export function RigImportBanner({ rigImport }: { rigImport: RigImport }) {
  const { phase, accept, decline, dismiss } = rigImport;

  if (phase.kind === 'offer' || phase.kind === 'importing') {
    const importing = phase.kind === 'importing';
    return (
      <section role="region" aria-label="Import browser Rigs" style={banner}>
        <span style={{ flex: 1 }}>
          {importing
            ? 'Importing your Rigs...'
            : `You have ${rigs(phase.rigs.length)} saved in this browser. Add ${phase.rigs.length === 1 ? 'it' : 'them'} to your Garage so ${phase.rigs.length === 1 ? 'it comes' : 'they come'} with your account? ${phase.rigs.length === 1 ? 'It stays' : 'They stay'} in this browser either way.`}
        </span>
        {!importing && (
          <>
            <button onClick={() => void accept()} style={action}>
              Import to my Garage
            </button>
            <button onClick={decline} style={link}>
              No thanks
            </button>
          </>
        )}
      </section>
    );
  }

  if (phase.kind === 'interrupted') {
    return (
      <div role="alert" style={banner}>
        <span style={{ flex: 1 }}>
          The import didn't finish. Nothing is added twice, so it is safe to try again.
        </span>
        <button onClick={() => void accept()} style={action}>
          Try again
        </button>
        <button onClick={dismiss} style={link}>
          Not now
        </button>
      </div>
    );
  }

  if (phase.kind === 'done') {
    return (
      <div role="status" style={banner}>
        <span style={{ flex: 1 }}>{resultText(phase.result)}</span>
        <button onClick={dismiss} style={link}>
          Dismiss
        </button>
      </div>
    );
  }

  return null;
}
