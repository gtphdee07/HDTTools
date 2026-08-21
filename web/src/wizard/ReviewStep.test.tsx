import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { MODULES } from '../mockData';
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
});
