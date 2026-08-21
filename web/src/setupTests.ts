import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'
import '@testing-library/jest-dom/vitest'

// Without globals: true in vite.config.ts, @testing-library/react's
// automatic afterEach(cleanup) never registers (it only self-wires when
// it finds a global afterEach) - unmounting explicitly here, once, is
// simpler than remembering it in every test file.
afterEach(() => {
  cleanup()
})
