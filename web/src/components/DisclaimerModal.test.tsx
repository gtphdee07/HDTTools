import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { DisclaimerModal } from './DisclaimerModal';

describe('DisclaimerModal', () => {
  it('renders the disclaimer heading', () => {
    render(<DisclaimerModal onAcknowledge={vi.fn()} />);
    expect(screen.getByText('⚠️ Experimental Tool — Not for Safety Decisions')).toBeInTheDocument();
  });

  it('calls onAcknowledge when "I Understand — Continue" is clicked', async () => {
    const onAcknowledge = vi.fn();
    render(<DisclaimerModal onAcknowledge={onAcknowledge} />);

    await userEvent.click(screen.getByRole('button', { name: 'I Understand — Continue' }));

    expect(onAcknowledge).toHaveBeenCalled();
  });
});
