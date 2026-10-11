import { existsSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';
import { fetchChunks, runBundle, type RunningBundle } from './bundleLoader';

// Fixture for a code-split Vite build: the entry reads import.meta and dynamically imports a chunk, and the
// chunk statically imports a shared chunk. No network: fetchText serves these from memory.
const ORIGIN = 'https://site.example';
const ENTRY = `${ORIGIN}/assets/index-AbC.js`;
const CHUNK = `${ORIGIN}/assets/Lazy-Def.js`;
const SHARED = `${ORIGIN}/assets/shared-Ghi.js`;

const g = globalThis as unknown as Record<string, unknown>;

const fixture = (marker: string): Record<string, string> => ({
  [ENTRY]: [
    `const here = import.meta.url;`,
    `const resolved = import.meta.resolve ? import.meta.resolve('./Lazy-Def.js') : 'none';`,
    `const lazy = await import(\`./Lazy-Def.js\`);`,
    `globalThis.${marker} = { here, resolved, lazy: lazy.lazyValue };`,
  ].join('\n'),
  [CHUNK]: `import{shared as s}from"./shared-Ghi.js";export const lazyValue = s + 1;`,
  [SHARED]: `export const shared = 41;`,
});

const serve = (files: Record<string, string>, requested: string[] = []) => async (url: string) => {
  requested.push(url);
  const text = files[url];
  if (text === undefined) throw new Error('HTTP 404');
  return text;
};

describe('fetchChunks', () => {
  it('follows static and dynamic imports from the entry, once each', async () => {
    const requested: string[] = [];
    const bundle = await fetchChunks(ENTRY, fixture('__unused')[ENTRY], serve(fixture('__unused'), requested));

    expect([...bundle.files.keys()].sort()).toEqual([CHUNK, ENTRY, SHARED].sort());
    expect(requested.sort()).toEqual([CHUNK, SHARED].sort());
  });

  it('copes with a chunk that imports the entry back', async () => {
    const files = {
      [ENTRY]: `import("./Lazy-Def.js");`,
      [CHUNK]: `import{x}from"./index-AbC.js";export const lazyValue = 1;`,
    };
    const bundle = await fetchChunks(ENTRY, files[ENTRY], serve(files));
    expect([...bundle.files.keys()].sort()).toEqual([CHUNK, ENTRY].sort());
  });

  it('ignores relative-looking strings that are not import specifiers', async () => {
    const entry = `const doc = "see ./README.js for details"; const css = "./style.css";`;
    const bundle = await fetchChunks(ENTRY, entry, serve({}));
    expect([...bundle.files.keys()]).toEqual([ENTRY]);
  });

  it('fails naming the chunk when a chunk cannot be fetched', async () => {
    const files = fixture('__unused');
    delete files[SHARED];
    await expect(fetchChunks(ENTRY, files[ENTRY], serve(files))).rejects.toThrow(/chunk .*shared-Ghi\.js/);
  });
});

describe('runBundle', () => {
  let running: RunningBundle | undefined;
  afterEach(async () => {
    await running?.dispose();
    running = undefined;
  });

  it('runs a split bundle that uses import.meta and a dynamic import()', async () => {
    const files = fixture('__splitRan');
    running = await runBundle(await fetchChunks(ENTRY, files[ENTRY], serve(files)));

    const ran = g.__splitRan as { here: string; resolved: string; lazy: number };
    expect(ran.here).toMatch(/^file:.*index-AbC\.js$/);
    expect(ran.resolved).toMatch(/Lazy-Def\.js$/);
    expect(ran.lazy).toBe(42);
  });

  it('runs the entry in this process, so it sees the page globals', async () => {
    const files = { [ENTRY]: `globalThis.__sawDocument = typeof document !== 'undefined';` };
    running = await runBundle(await fetchChunks(ENTRY, files[ENTRY], serve(files)));
    expect(g.__sawDocument).toBe(true);
  });

  it('fails naming the chunk when a chunk throws as it loads, even if the entry never reaches it', async () => {
    const files = {
      [ENTRY]: `globalThis.__lazyEntry = true; export const later = () => import("./Lazy-Def.js");`,
      [CHUNK]: `throw new Error("boom in chunk");`,
    };
    const bundle = await fetchChunks(ENTRY, files[ENTRY], serve(files));
    const failure = await runBundle(bundle).then(
      () => undefined,
      (e: unknown) => e as Error,
    );
    expect(failure?.message).toMatch(/chunk .*Lazy-Def\.js/);
    expect(failure?.message).toContain('boom in chunk');
  });

  it('fails naming the chunk for a syntax error, not a bare SyntaxError', async () => {
    const files = {
      [ENTRY]: `import("./Lazy-Def.js").catch(() => {});`,
      [CHUNK]: `export const = ;`,
    };
    const bundle = await fetchChunks(ENTRY, files[ENTRY], serve(files));
    const failure = await runBundle(bundle).then(
      () => undefined,
      (e: unknown) => e as Error,
    );
    expect(failure?.message).toMatch(/^Could not run chunk .*Lazy-Def\.js/);
    expect(failure?.message).toContain('SyntaxError');
  });

  it('blames the chunk, not the entry, when the entry imports a broken chunk statically', async () => {
    const files = {
      [ENTRY]: `import{lazyValue}from"./Lazy-Def.js";globalThis.__neverRuns = lazyValue;`,
      [CHUNK]: `export const = ;`,
    };
    const bundle = await fetchChunks(ENTRY, files[ENTRY], serve(files));
    const failure = await runBundle(bundle).then(
      () => undefined,
      (e: unknown) => e as Error,
    );
    expect(failure?.message).toMatch(/^Could not run chunk .*Lazy-Def\.js/);
    expect(g.__neverRuns).toBeUndefined();
  });

  it('fails naming the entry script when the entry itself cannot run', async () => {
    const files = { [ENTRY]: `throw new Error("boom in entry");` };
    const bundle = await fetchChunks(ENTRY, files[ENTRY], serve(files));
    await expect(runBundle(bundle)).rejects.toThrow(/entry script .*index-AbC\.js.*boom in entry/);
  });

  it('removes its temporary files on dispose', async () => {
    const files = fixture('__disposeRan');
    running = await runBundle(await fetchChunks(ENTRY, files[ENTRY], serve(files)));
    expect(existsSync(running.dir)).toBe(true);
    await running.dispose();
    expect(existsSync(running.dir)).toBe(false);
  });
});
