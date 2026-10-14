import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import type { RecentRig } from '../types';
import { Button } from '../design-system/Button';

// The delete control for a saved Rig, shared by the wizard's Rig list and the Dashboard's Rig cards
// (#90, #106) so both confirm and fail the same way. The caller keeps one "which Rig is being asked
// about" value, shows RigDeleteButton on each Rig, and mounts RigDeleteConfirm for the asked one. It
// passes `onDeleteRig` only when Rigs can be deleted (a signed-in account), and then shows no control
// at all otherwise.

// Resolves true once the Rig is gone, false if it could not be deleted and is still there.
export type DeleteRig = (rig: RecentRig) => Promise<boolean>;

export function RigDeleteButton({ rig, onAsk }: { rig: RecentRig; onAsk: () => void }) {
  return (
    <button
      aria-label={`Delete ${rig.nickname}`}
      title="Delete this rig"
      onClick={(e) => {
        // The control sits on a card that starts a check when clicked; it must not.
        e.stopPropagation();
        onAsk();
      }}
      style={{
        display: 'flex',
        padding: 8,
        background: 'none',
        border: 'none',
        color: 'var(--fg-2)',
        cursor: 'pointer',
      }}
    >
      <Trash2 size={18} aria-hidden="true" />
    </button>
  );
}

// Asks, then deletes. `onDone` fires when the user cancels or the Rig is gone, so the caller can
// stop showing it; after a failed delete it stays, with the error, for another try.
export function RigDeleteConfirm({ rig, onDelete, onDone }: { rig: RecentRig; onDelete: DeleteRig; onDone: () => void }) {
  const [deleting, setDeleting] = useState(false);
  const [failed, setFailed] = useState(false);

  const confirm = async () => {
    setDeleting(true);
    setFailed(false);
    const deleted = await onDelete(rig);
    setDeleting(false);
    if (deleted) onDone();
    else setFailed(true);
  };

  return (
    <div onClick={(e) => e.stopPropagation()} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ fontSize: 14, color: 'var(--fg-1)' }}>
        Delete "{rig.nickname}"? This frees its spot in your Garage and can't be undone.
      </div>
      {failed && (
        <div role="alert" style={{ fontSize: 14, color: 'var(--fg-1)' }}>
          We couldn't delete "{rig.nickname}". It's still in your Garage; please try again.
        </div>
      )}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
        <Button variant="primary" size="sm" disabled={deleting} onClick={() => void confirm()}>
          {deleting ? 'Deleting…' : 'Yes, delete'}
        </Button>
        <Button variant="ghost" size="sm" disabled={deleting} onClick={onDone}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
