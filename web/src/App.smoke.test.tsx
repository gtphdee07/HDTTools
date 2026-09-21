import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import App from './App';

// Proves the Vitest + React Testing Library harness itself works (jsdom
// environment, setupTests' jest-dom matchers, App's localStorage/
// sessionStorage reads on mount) before any real interaction tests are
// written against it.
describe('App', () => {
  it('renders the home screen', () => {
    render(<App />);
    // "RigCheck" appears in both the header and footer branding.
    expect(screen.getAllByText('RigCheck').length).toBeGreaterThanOrEqual(1);
  });
});
