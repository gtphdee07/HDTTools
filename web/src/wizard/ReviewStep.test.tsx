import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { MODULES } from '../mockData';
import { ScanError } from '../scanError';
import type { ScanErrorCode } from '../scanError';
import { ReviewStep } from './ReviewStep';

const TRUCK_MODULE = MODULES[1];
const TRAILER_MODULE = MODULES[2];

function baseProps(overrides: Partial<Parameters<typeof ReviewStep>[0]> = {}) {
  return {
    module: TRUCK_MODULE,
    data: {},
    error: null,
    onFieldChange: vi.fn(),
    onContinue: vi.fn(),
    ...overrides,
  };
}

describe('ReviewStep', () => {
  it("renders each of the module's fields with the given data, blank when a field is missing", () => {
    render(<ReviewStep {...baseProps({ data: { gvwr_lb: 14000 } })} />);

    expect(screen.getByLabelText('GVWR (lb)')).toHaveValue(14000);
    expect(screen.getByLabelText('Manufacturer')).toHaveValue('');
  });

  it('calls onFieldChange with the field name, isNumber flag, and raw value when typed into', async () => {
    const onFieldChange = vi.fn();
    render(<ReviewStep {...baseProps({ onFieldChange })} />);

    await userEvent.type(screen.getByLabelText('GVWR (lb)'), '1');

    expect(onFieldChange).toHaveBeenCalledWith('gvwr_lb', true, '1');
  });

  it("calls onContinue when the module's continue button is clicked", async () => {
    const onContinue = vi.fn();
    render(<ReviewStep {...baseProps({ onContinue })} />);

    await userEvent.click(screen.getByRole('button', { name: TRUCK_MODULE.continueLabel }));

    expect(onContinue).toHaveBeenCalled();
  });

  it('shows the error message when provided', () => {
    render(<ReviewStep {...baseProps({ error: 'Please fix the GVWR field.' })} />);
    expect(screen.getByText('Please fix the GVWR field.')).toBeInTheDocument();
  });

  it('does not render the stand-alone-weight scan section for a non-truck module', () => {
    render(
      <ReviewStep
        {...baseProps({
          module: TRAILER_MODULE,
          pinWeightPct: 20,
          onPinWeightPctChange: vi.fn(),
          onScanStandaloneTicket: vi.fn(),
        })}
      />,
    );
    expect(screen.queryByText("Don't know your tow vehicle's stand-alone weight?")).not.toBeInTheDocument();
  });

  it('does not render the scan section for the truck module when onScanStandaloneTicket is omitted', () => {
    render(<ReviewStep {...baseProps()} />);
    expect(screen.queryByText("Don't know your tow vehicle's stand-alone weight?")).not.toBeInTheDocument();
  });

  it('shows the pin-weight slider when stand-alone weight is unknown, hides it once known', () => {
    const { rerender } = render(
      <ReviewStep
        {...baseProps({
          data: {},
          pinWeightPct: 20,
          onPinWeightPctChange: vi.fn(),
          onScanStandaloneTicket: vi.fn(),
        })}
      />,
    );
    expect(screen.getByRole('slider')).toBeInTheDocument();

    rerender(
      <ReviewStep
        {...baseProps({
          data: { standalone_weight_lb: 6000 },
          pinWeightPct: 20,
          onPinWeightPctChange: vi.fn(),
          onScanStandaloneTicket: vi.fn(),
        })}
      />,
    );
    expect(screen.queryByRole('slider')).not.toBeInTheDocument();
  });

  it('calls onPinWeightPctChange with the numeric slider value', async () => {
    const onPinWeightPctChange = vi.fn();
    render(
      <ReviewStep
        {...baseProps({
          pinWeightPct: 20,
          onPinWeightPctChange,
          onScanStandaloneTicket: vi.fn(),
        })}
      />,
    );

    // fireEvent, not userEvent - jsdom/user-event's pointer-based drag
    // simulation doesn't reliably move a type="range" input.
    fireEvent.change(screen.getByRole('slider'), { target: { value: '15' } });

    expect(onPinWeightPctChange).toHaveBeenCalledWith(15);
  });

  it('scanning a standalone ticket shows "Reading…" while pending, then calls onScanStandaloneTicket with the file', async () => {
    let resolveScan: () => void = () => {};
    const onScanStandaloneTicket = vi.fn(
      () => new Promise<void>((resolve) => { resolveScan = resolve; }),
    );
    const { container } = render(
      <ReviewStep {...baseProps({ pinWeightPct: 20, onPinWeightPctChange: vi.fn(), onScanStandaloneTicket })} />,
    );
    const file = new File(['x'], 'standalone.jpg', { type: 'image/jpeg' });
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;

    await userEvent.upload(input, file);

    expect(onScanStandaloneTicket).toHaveBeenCalledWith(file);
    expect(screen.getByRole('button', { name: 'Reading…' })).toBeDisabled();

    resolveScan();
    expect(await screen.findByRole('button', { name: 'Scan tow-vehicle-only ticket' })).toBeEnabled();
  });

  it("shows the scan's own error message, separate from the error prop, when onScanStandaloneTicket rejects", async () => {
    const onScanStandaloneTicket = vi.fn().mockRejectedValue(new Error("Couldn't find a weight on that ticket."));
    const { container } = render(
      <ReviewStep {...baseProps({ pinWeightPct: 20, onPinWeightPctChange: vi.fn(), onScanStandaloneTicket })} />,
    );
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;

    await userEvent.upload(input, new File(['x'], 'standalone.jpg', { type: 'image/jpeg' }));

    expect(await screen.findByText("Couldn't find a weight on that ticket.")).toBeInTheDocument();
  });

  it('"Try again" after a failed ticket scan re-runs it with the same File, without the photo picker', async () => {
    const onScanStandaloneTicket = vi.fn().mockRejectedValueOnce(new Error('No connection.')).mockResolvedValueOnce(undefined);
    const { container } = render(
      <ReviewStep {...baseProps({ pinWeightPct: 20, onPinWeightPctChange: vi.fn(), onScanStandaloneTicket })} />,
    );
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const click = vi.spyOn(input, 'click');
    const file = new File(['x'], 'standalone.jpg', { type: 'image/jpeg' });
    await userEvent.upload(input, file);
    await userEvent.click(await screen.findByRole('button', { name: 'Try again' }));

    await waitFor(() => expect(onScanStandaloneTicket).toHaveBeenCalledTimes(2));
    expect(onScanStandaloneTicket.mock.calls[1][0]).toBe(file);
    expect(click).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
  });

  describe('what a ticket scan that did not deliver offers next', () => {
    const failWith = async (code: ScanErrorCode) => {
      const onScanStandaloneTicket = vi.fn().mockRejectedValue(new ScanError(code, 'It did not work.'));
      const { container } = render(
        <ReviewStep {...baseProps({ pinWeightPct: 20, onPinWeightPctChange: vi.fn(), onScanStandaloneTicket })} />,
      );
      const input = container.querySelector('input[type="file"]') as HTMLInputElement;
      await userEvent.upload(input, new File(['x'], 'standalone.jpg', { type: 'image/jpeg' }));
      await screen.findByText('It did not work.');
      return { input, onScanStandaloneTicket };
    };

    const retryable: ScanErrorCode[] = [
      'auth_unavailable',
      'extraction_failed',
      'extraction_failed_no_refund',
      'billing_error',
      'network',
      'unknown',
      'timeout',
    ];
    for (const code of retryable) {
      it(`offers "Try again" after ${code}, and no different-photo prompt`, async () => {
        await failWith(code);

        expect(screen.getByRole('button', { name: 'Try again' })).toBeEnabled();
        expect(screen.queryByRole('button', { name: 'Choose a different photo' })).not.toBeInTheDocument();
      });
    }

    for (const code of ['unauthorized', 'bad_request', 'bad_photo'] as const) {
      it(`offers "Choose a different photo", not "Try again", after ${code}`, async () => {
        const { input } = await failWith(code);
        const click = vi.spyOn(input, 'click');

        expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Type it in' })).not.toBeInTheDocument();
        await userEvent.click(screen.getByRole('button', { name: 'Choose a different photo' }));

        expect(click).toHaveBeenCalled();
      });
    }

    it('offers "Choose a different photo" and "Type it in", not "Try again", after the no-weight answer', async () => {
      const { input } = await failWith('no_weight');
      const click = vi.spyOn(input, 'click');

      expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
      await userEvent.click(screen.getByRole('button', { name: 'Choose a different photo' }));
      expect(click).toHaveBeenCalled();

      await userEvent.click(screen.getByRole('button', { name: 'Type it in' }));
      expect(screen.getByLabelText('Stand-alone Weight (lb, optional)')).toHaveFocus();
    });

    it('still offers "Choose a different photo" after unauthorized while the user is told to sign in again', async () => {
      const onScanStandaloneTicket = vi.fn().mockRejectedValue(new ScanError('unauthorized', 'It did not work.'));
      const props = baseProps({ pinWeightPct: 20, onPinWeightPctChange: vi.fn(), onScanStandaloneTicket });
      const { container, rerender } = render(<ReviewStep {...props} scanAccess={{ kind: 'ready', balance: 1 }} onGoAccount={vi.fn()} onRetryScanAccess={vi.fn()} />);
      const input = container.querySelector('input[type="file"]') as HTMLInputElement;
      await userEvent.upload(input, new File(['x'], 'standalone.jpg', { type: 'image/jpeg' }));
      await screen.findByText('It did not work.');

      rerender(<ReviewStep {...props} scanAccess={{ kind: 'sign-in-again' }} onGoAccount={vi.fn()} onRetryScanAccess={vi.fn()} />);
      const click = vi.spyOn(input, 'click');

      expect(screen.getByRole('button', { name: 'Sign in again' })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Scan tow-vehicle-only ticket' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
      await userEvent.click(screen.getByRole('button', { name: 'Choose a different photo' }));
      expect(click).toHaveBeenCalled();
    });

    it('still offers "Type it in" after a no-weight answer that used the last scan, but no way to scan another photo', async () => {
      const onScanStandaloneTicket = vi.fn().mockRejectedValue(new ScanError('no_weight', 'It did not work.'));
      const props = baseProps({ pinWeightPct: 20, onPinWeightPctChange: vi.fn(), onScanStandaloneTicket });
      const { container, rerender } = render(<ReviewStep {...props} scanAccess={{ kind: 'ready', balance: 1 }} onGoAccount={vi.fn()} onRetryScanAccess={vi.fn()} />);
      const input = container.querySelector('input[type="file"]') as HTMLInputElement;
      await userEvent.upload(input, new File(['x'], 'standalone.jpg', { type: 'image/jpeg' }));
      await screen.findByText('It did not work.');

      rerender(<ReviewStep {...props} scanAccess={{ kind: 'no-scans' }} onGoAccount={vi.fn()} onRetryScanAccess={vi.fn()} />);

      expect(screen.queryByRole('button', { name: 'Choose a different photo' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
      await userEvent.click(screen.getByRole('button', { name: 'Type it in' }));
      expect(screen.getByLabelText('Stand-alone Weight (lb, optional)')).toHaveFocus();
    });

    it('clears the different-photo prompt when the next scan starts', async () => {
      const { onScanStandaloneTicket, input } = await failWith('bad_request');
      onScanStandaloneTicket.mockResolvedValue(undefined);

      await userEvent.upload(input, new File(['y'], 'other.jpg', { type: 'image/jpeg' }));

      await waitFor(() => expect(onScanStandaloneTicket).toHaveBeenCalledTimes(2));
      expect(screen.queryByRole('button', { name: 'Choose a different photo' })).not.toBeInTheDocument();
    });
  });

  it('offers no "Try again" once the user can no longer scan, as when the failed scan used their last scan', async () => {
    const onScanStandaloneTicket = vi.fn().mockRejectedValue(new Error("Couldn't find a weight on that ticket."));
    const props = baseProps({ pinWeightPct: 20, onPinWeightPctChange: vi.fn(), onScanStandaloneTicket });
    const { container, rerender } = render(<ReviewStep {...props} scanAccess={{ kind: 'ready', balance: 1 }} onGoAccount={vi.fn()} onRetryScanAccess={vi.fn()} />);
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, new File(['x'], 'standalone.jpg', { type: 'image/jpeg' }));
    expect(await screen.findByRole('button', { name: 'Try again' })).toBeInTheDocument();

    rerender(<ReviewStep {...props} scanAccess={{ kind: 'no-scans' }} onGoAccount={vi.fn()} onRetryScanAccess={vi.fn()} />);

    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
  });

  it('clears the file input after a pick, so choosing the same photo again fires a change', async () => {
    const onScanStandaloneTicket = vi.fn().mockRejectedValue(new Error('No connection.'));
    const { container } = render(
      <ReviewStep {...baseProps({ pinWeightPct: 20, onPinWeightPctChange: vi.fn(), onScanStandaloneTicket })} />,
    );
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;

    await userEvent.upload(input, new File(['x'], 'standalone.jpg', { type: 'image/jpeg' }));
    await screen.findByText('No connection.');

    expect(input.value).toBe('');
  });
});
