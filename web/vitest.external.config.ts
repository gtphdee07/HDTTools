import { defineConfig, loadEnv } from 'vite'

// Separate from vite.config.ts so `npm test` never reaches a live provider.
// Credentials come from the gitignored .env.local; a real shell variable wins.
// EXTERNAL_SURFACES (comma-separated, set by test-external.ps1) narrows the run to
// tests whose name carries a "[surface]" tag; unset runs every external test.
const surfaces = (process.env.EXTERNAL_SURFACES ?? '').split(',').filter(Boolean)

export default defineConfig(({ mode }) => ({
  test: {
    environment: 'node',
    include: ['src/**/*.external.test.ts'],
    env: loadEnv(mode, process.cwd(), ['VITE_SUPABASE_', 'WEB_EXTERNAL_']),
    testNamePattern: surfaces.length > 0 ? new RegExp(String.raw`\[(${surfaces.join('|')})\]`) : undefined,
    testTimeout: 30_000,
    hookTimeout: 30_000,
  },
}))
