/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import { configDefaults } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    exclude: [...configDefaults.exclude, 'src/**/*.external.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary'],
      // Scope the report to application code: without this, v8 only reports
      // files a test happened to import, so an unimported file (main.tsx) is
      // silently absent instead of showing up as an uncovered gap.
      include: ['src/**'],
    },
  },
})
