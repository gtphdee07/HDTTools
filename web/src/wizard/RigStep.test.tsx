import { useState } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { RecentRig } from '../types';
import { RigStep } from './RigStep';

function rig(overrides: Partial<RecentRig> = {}): RecentRig {
  return {
    nickname: 'Big Blue',
    truck: { manufacturer: 'Ford' },
    trailer: { manufacturer: 'Forest River' },
    lastUsedAt: '2026-08-21T00:00:00.000Z',
    ...overrides,
  };
}

function baseProps(overrides: Partial<Parameters<typeof RigStep>[0]> = {}) {
  return {
    recentRigs: [],
    onSelectExisting: vi.fn(),
    onStartNew: vi.fn(),
    onDeleteRig: vi.fn(async () => true),
    ...overrides,
  };
}

describe('RigStep', () => {
  it('renders no rig cards when there are no recent rigs', () => {
    render(<RigStep {...baseProps()} />);
    expect(screen.queryByText('CHOOSE')).not.toBeInTheDocument();
  });

  it("renders each recent rig's nickname and a manufacturer subtitle when both are known", () => {
    render(<RigStep {...baseProps({ recentRigs: [rig()] })} />);
    expect(screen.getByText('Big Blue')).toBeInTheDocument();
    expect(screen.getByText('Ford + Forest River')).toBeInTheDocument();
  });

  it('omits the subtitle line when neither manufacturer is known', () => {
    render(<RigStep {...baseProps({ recentRigs: [rig({ truck: {}, trailer: {} })] })} />);
    expect(screen.getByText('Big Blue')).toBeInTheDocument();
    expect(screen.queryByText('Ford')).not.toBeInTheDocument();
    expect(screen.queryByText('+')).not.toBeInTheDocument();
  });

  it('calls onSelectExisting with the clicked rig', async () => {
    const onSelectExisting = vi.fn();
    const theRig = rig();
    render(<RigStep {...baseProps({ recentRigs: [theRig], onSelectExisting })} />);

    await userEvent.click(screen.getByText('Big Blue'));

    expect(onSelectExisting).toHaveBeenCalledWith(theRig);
  });

  it('disables Start New Rig until a non-blank nickname is typed', async () => {
    render(<RigStep {...baseProps()} />);
    const button = screen.getByRole('button', { name: 'Start New Rig' });
    expect(button).toBeDisabled();

    await userEvent.type(screen.getByPlaceholderText('e.g. Big Blue'), 'Red Rocket');

    expect(button).toBeEnabled();
  });

  it('keeps Start New Rig disabled for a whitespace-only nickname', async () => {
    render(<RigStep {...baseProps()} />);

    await userEvent.type(screen.getByPlaceholderText('e.g. Big Blue'), '   ');

    expect(screen.getByRole('button', { name: 'Start New Rig' })).toBeDisabled();
  });

  it('calls onStartNew with the trimmed nickname', async () => {
    const onStartNew = vi.fn();
    render(<RigStep {...baseProps({ onStartNew })} />);

    await userEvent.type(screen.getByPlaceholderText('e.g. Big Blue'), '  Red Rocket  ');
    await userEvent.click(screen.getByRole('button', { name: 'Start New Rig' }));

    expect(onStartNew).toHaveBeenCalledWith('Red Rocket');
  });
});

describe('RigStep delete', () => {
  it('shows no delete control when Rigs cannot be deleted', () => {
    render(<RigStep {...baseProps({ recentRigs: [rig()], onDeleteRig: undefined })} />);

    expect(screen.getByText('Big Blue')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete Big Blue' })).not.toBeInTheDocument();
  });

  it('asks for confirmation naming the Rig before deleting anything', async () => {
    const onDeleteRig = vi.fn(async () => true);
    render(<RigStep {...baseProps({ recentRigs: [rig()], onDeleteRig })} />);

    await userEvent.click(screen.getByRole('button', { name: 'Delete Big Blue' }));

    expect(screen.getByText(/delete .*Big Blue.*\?/i)).toBeInTheDocument();
    expect(onDeleteRig).not.toHaveBeenCalled();
  });

  it('deletes the Rig once the user confirms', async () => {
    const onDeleteRig = vi.fn(async () => true);
    const theRig = rig();
    render(<RigStep {...baseProps({ recentRigs: [theRig], onDeleteRig })} />);

    await userEvent.click(screen.getByRole('button', { name: 'Delete Big Blue' }));
    await userEvent.click(screen.getByRole('button', { name: 'Yes, delete' }));

    expect(onDeleteRig).toHaveBeenCalledWith(theRig);
  });

  it('deletes nothing when the user cancels, and does not start a check either', async () => {
    const onDeleteRig = vi.fn(async () => true);
    const onSelectExisting = vi.fn();
    render(<RigStep {...baseProps({ recentRigs: [rig()], onDeleteRig, onSelectExisting })} />);

    await userEvent.click(screen.getByRole('button', { name: 'Delete Big Blue' }));
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(onDeleteRig).not.toHaveBeenCalled();
    expect(onSelectExisting).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Delete Big Blue' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Yes, delete' })).not.toBeInTheDocument();
  });

  it('opening the delete control does not select the Rig for a check', async () => {
    const onSelectExisting = vi.fn();
    render(<RigStep {...baseProps({ recentRigs: [rig()], onSelectExisting })} />);

    await userEvent.click(screen.getByRole('button', { name: 'Delete Big Blue' }));
    await userEvent.click(screen.getByRole('button', { name: 'Yes, delete' }));

    expect(onSelectExisting).not.toHaveBeenCalled();
  });

  it('shows an error and keeps the Rig when the delete fails', async () => {
    const onDeleteRig = vi.fn(async () => false);
    render(<RigStep {...baseProps({ recentRigs: [rig()], onDeleteRig })} />);

    await userEvent.click(screen.getByRole('button', { name: 'Delete Big Blue' }));
    await userEvent.click(screen.getByRole('button', { name: 'Yes, delete' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/couldn.t delete.*Big Blue/i);
    expect(screen.getByText('Big Blue')).toBeInTheDocument();
  });
});

// Keyboard and screen-reader behaviour of the shared delete control (#108): focus follows the user
// through ask / cancel / delete / fail instead of dropping back to the page.
describe('RigStep delete focus', () => {
  // Removes a Rig from the list the way the app does once a delete succeeds.
  function Harness({ onDeleteRig }: { onDeleteRig: (r: RecentRig) => Promise<boolean> }) {
    const [rigs, setRigs] = useState([rig({ nickname: 'Big Blue' }), rig({ nickname: 'Little Red' })]);
    return (
      <RigStep
        {...baseProps({
          recentRigs: rigs,
          onDeleteRig: async (r: RecentRig) => {
            const ok = await onDeleteRig(r);
            if (ok) setRigs((all) => all.filter((x) => x.nickname !== r.nickname));
            return ok;
          },
        })}
      />
    );
  }

  it('moves focus to Cancel when the confirmation opens, and labels the question with the Rig', async () => {
    render(<Harness onDeleteRig={async () => true} />);

    await userEvent.click(screen.getByRole('button', { name: 'Delete Big Blue' }));

    const cancel = screen.getByRole('button', { name: 'Cancel' });
    expect(cancel).toHaveFocus();
    expect(screen.getByRole('group', { name: /Delete "Big Blue"\?/ })).toContainElement(cancel);
    // A screen reader reads the question when focus lands on Cancel, not only the group's name.
    expect(cancel).toHaveAccessibleDescription(/Delete "Big Blue"\?/);
  });

  it("returns focus to the same Rig's bin when the user cancels", async () => {
    render(<Harness onDeleteRig={async () => true} />);

    await userEvent.click(screen.getByRole('button', { name: 'Delete Little Red' }));
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(screen.getByRole('button', { name: 'Delete Little Red' })).toHaveFocus();
  });

  it('puts focus on the page heading after a successful delete', async () => {
    render(<Harness onDeleteRig={async () => true} />);

    await userEvent.click(screen.getByRole('button', { name: 'Delete Big Blue' }));
    await userEvent.click(screen.getByRole('button', { name: 'Yes, delete' }));

    await waitFor(() => expect(screen.queryByText('Big Blue')).not.toBeInTheDocument());
    expect(screen.getByRole('heading', { name: 'Which rig are we checking?' })).toHaveFocus();
  });

  it('announces the failure and keeps focus on the button just used when the delete fails', async () => {
    render(<Harness onDeleteRig={async () => false} />);

    await userEvent.click(screen.getByRole('button', { name: 'Delete Big Blue' }));
    await userEvent.click(screen.getByRole('button', { name: 'Yes, delete' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/couldn.t delete.*Big Blue/i);
    expect(screen.getByRole('button', { name: 'Yes, delete' })).toHaveFocus();
  });
});
