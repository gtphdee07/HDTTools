import { useEffect, useId, useRef, useState } from 'react';
import { Trash2 } from 'lucide-react';
import type { RecentRig } from '../types';
import { Button } from '../design-system/Button';

// The delete control for a saved Rig, shared by the wizard's Rig list and the Dashboard's Rig cards
// (#90, #106) so both confirm and fail the same way. The caller calls `useRigDelete()`, shows
// RigDeleteButton on each Rig, and mounts RigDeleteConfirm for the asked one. It passes `onDeleteRig`
// only when Rigs can be deleted (a signed-in account), and then shows no control at all otherwise.
//
// Keyboard focus (#108): opening the confirmation moves focus to Cancel; cancelling puts it back on
// that Rig's bin; a delete that succeeds moves it to the section heading (`headingRef`, which the
// caller puts on its heading with tabIndex={-1}) because the Rig and its bin are gone; a delete that
// fails leaves it on "Yes, delete".

// Resolves true once the Rig is gone, false if it could not be deleted and is still there.
export type DeleteRig = (rig: RecentRig) => Promise<boolean>;

export function useRigDelete() {
  // Nickname of the Rig being asked about, being deleted, or that failed to delete.
  const [confirming, setConfirming] = useState<string | null>(null);
  // Nickname of the Rig whose bin should take focus when it next appears (after a cancel).
  const [refocusBin, setRefocusBin] = useState<string | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);

  return {
    confirming,
    refocusBin,
    headingRef,
    ask: (nickname: string) => {
      setConfirming(nickname);
      setRefocusBin(null);
    },
    cancel: (nickname: string) => {
      setConfirming(null);
      setRefocusBin(nickname);
    },
    deleted: () => {
      setConfirming(null);
      setRefocusBin(null);
      headingRef.current?.focus();
    },
  };
}

export function RigDeleteButton({ rig, onAsk, takeFocus = false }: { rig: RecentRig; onAsk: () => void; takeFocus?: boolean }) {
  const ref = useRef<HTMLButtonElement>(null);
  // Only when the bin first appears: it comes back after a cancel and the user was last on it.
  useEffect(() => {
    if (takeFocus) ref.current?.focus();
  }, []);

  return (
    <button
      ref={ref}
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

// Asks, then deletes. `onCancel` fires when the user cancels and `onDeleted` when the Rig is gone, so
// the caller can stop showing it; after a failed delete it stays, with the error, for another try.
export function RigDeleteConfirm({
  rig,
  onDelete,
  onCancel,
  onDeleted,
}: {
  rig: RecentRig;
  onDelete: DeleteRig;
  onCancel: () => void;
  onDeleted: () => void;
}) {
  const [deleting, setDeleting] = useState(false);
  const [failed, setFailed] = useState(false);
  const questionId = useId();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);

  // Cancel is the safe choice, and moving focus into the group makes a screen reader read its name
  // (the question) as the user arrives.
  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  // The button was disabled while the delete ran, which can drop focus; give it back for the retry.
  useEffect(() => {
    if (failed && !deleting) confirmRef.current?.focus();
  }, [failed, deleting]);

  const confirm = async () => {
    setDeleting(true);
    setFailed(false);
    const deleted = await onDelete(rig);
    setDeleting(false);
    if (deleted) onDeleted();
    else setFailed(true);
  };

  return (
    <div
      role="group"
      aria-labelledby={questionId}
      onClick={(e) => e.stopPropagation()}
      style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
    >
      <div id={questionId} style={{ fontSize: 14, color: 'var(--fg-1)' }}>
        Delete "{rig.nickname}"? This frees its spot in your Garage and can't be undone.
      </div>
      {failed && (
        <div role="alert" style={{ fontSize: 14, color: 'var(--fg-1)' }}>
          We couldn't delete "{rig.nickname}". It's still in your Garage; please try again.
        </div>
      )}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
        <Button ref={confirmRef} variant="primary" size="sm" disabled={deleting} onClick={() => void confirm()}>
          {deleting ? 'Deleting…' : 'Yes, delete'}
        </Button>
        <Button ref={cancelRef} variant="ghost" size="sm" disabled={deleting} onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
