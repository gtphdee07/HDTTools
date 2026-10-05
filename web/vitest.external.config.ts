import { defineConfig, loadEnv } from 'vite'

// Separate from vite.config.ts so `npm test` never reaches a live provider.
// Credentials come from the gitignored .env.local; a real shell variable wins.
// EXTERNAL_SURFACES (comma-separated, set by test-external.ps1) narrows the run to
// tests whose name carries a "[surface]" tag; unset runs every external test.
//
// The Pages-site test evaluates the live site's JS bundle inside its worker, so it runs as its own
// project with only the public Supabase variables: the test-account credentials (WEB_EXTERNAL_*) must
// never be in a worker that runs fetched code. Every other external test, including any new one,
// stays in the default project.
const surfaces = (process.env.EXTERNAL_SURFACES ?? '').split(',').filter(Boolean)

export default defineConfig(({ mode }) => {
  const shared = {
    environment: 'node' as const,
    testNamePattern: surfaces.length > 0 ? new RegExp(String.raw`\[(${surfaces.join('|')})\]`) : undefined,
    testTimeout: 30_000,
    hookTimeout: 30_000,
  }
  const envFor = (prefixes: string[]) => loadEnv(mode, process.cwd(), prefixes)

  return {
    test: {
      projects: [
        {
          test: {
            ...shared,
            name: 'external',
            include: ['src/**/*.external.test.ts'],
            exclude: ['src/**/pagesSite.external.test.ts'],
            env: envFor(['VITE_SUPABASE_', 'WEB_EXTERNAL_']),
          },
        },
        {
          test: {
            ...shared,
            name: 'pages-site',
            include: ['src/**/pagesSite.external.test.ts'],
            env: envFor(['VITE_SUPABASE_']),
          },
        },
      ],
    },
  }
})
