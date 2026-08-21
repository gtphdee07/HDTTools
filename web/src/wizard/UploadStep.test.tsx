import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { MODULES } from '../mockData';
import { UploadStep } from './UploadStep';

const TRUCK_MODULE = MODULES[1];
const SCALE_MODULE = MODULES[3];

function baseProps(overrides: Partial<Parameters<typeof UploadStep>[0]> = {}) {
  return {
    module: TRUCK_MODULE,
    file: null,
    error: null,
    onFileSelected: vi.fn(),
    onExtract: vi.fn(),
    onSkip: vi.fn(),
    ...overrides,
  };
}

describe('UploadStep', () => {
  it("renders the module's title and instructions", () => {
    render(<UploadStep {...baseProps()} />);
    expect(screen.getByText(TRUCK_MODULE.title)).toBeInTheDocument();
    expect(screen.getByText(TRUCK_MODULE.instructions)).toBeInTheDocument();
  });

  it('shows the slot placeholder and disables Extract Data when no file is selected', () => {
    render(<UploadStep {...baseProps()} />);
    expect(screen.getByText(TRUCK_MODULE.slotPlaceholder)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Extract Data' })).toBeDisabled();
  });

  it('shows the selected filename and enables Extract Data once a file is chosen', () => {
    const file = new File(['x'], 'truck.jpg', { type: 'image/jpeg' });
    render(<UploadStep {...baseProps({ file })} />);
    expect(screen.getByText('Selected: truck.jpg')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Extract Data' })).toBeEnabled();
  });

  it('calls onFileSelected with the chosen file', async () => {
    const onFileSelected = vi.fn();
    const { container } = render(<UploadStep {...baseProps({ onFileSelected })} />);
    const file = new File(['x'], 'truck.jpg', { type: 'image/jpeg' });
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;

    await userEvent.upload(input, file);

    expect(onFileSelected).toHaveBeenCalledWith(file);
  });

  it('calls onExtract when Extract Data is clicked with a file selected', async () => {
    const onExtract = vi.fn();
    const file = new File(['x'], 'truck.jpg', { type: 'image/jpeg' });
    render(<UploadStep {...baseProps({ file, onExtract })} />);

    await userEvent.click(screen.getByRole('button', { name: 'Extract Data' }));

    expect(onExtract).toHaveBeenCalled();
  });

  it('calls onSkip when "I don\'t have this image" is clicked, for a non-scale module', async () => {
    const onSkip = vi.fn();
    render(<UploadStep {...baseProps({ onSkip })} />);

    await userEvent.click(screen.getByRole('button', { name: "I don't have this image" }));

    expect(onSkip).toHaveBeenCalled();
  });

  it('shows the error message when provided', () => {
    render(<UploadStep {...baseProps({ error: 'Could not read that photo.' })} />);
    expect(screen.getByText('Could not read that photo.')).toBeInTheDocument();
  });

  it('does not render the scale-only hint or extra skip button for a non-scale module', () => {
    render(<UploadStep {...baseProps()} />);
    expect(screen.queryByText(/No CAT scale ticket\?/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Build Estimated Model / No CAT scale info' })).not.toBeInTheDocument();
  });

  it('renders the scale-specific hint and a second skip button for the scale module, both calling onSkip', async () => {
    const onSkip = vi.fn();
    render(<UploadStep {...baseProps({ module: SCALE_MODULE, onSkip })} />);

    expect(screen.getByText(/No CAT scale ticket\?/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: "I don't have this image" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'No Image / Enter Weight Manually' }));
    await userEvent.click(screen.getByRole('button', { name: 'Build Estimated Model / No CAT scale info' }));

    expect(onSkip).toHaveBeenCalledTimes(2);
  });
});
