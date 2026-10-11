// Runs a code-split production bundle (an entry script plus the chunks it imports) as real ES modules, for
// pagesSite.external.test.ts. A split build uses import.meta, dynamic import() and export, none of which a
// plain-script eval can run, so the files are written to a temp directory that mirrors their URL paths and the
// entry is imported natively. Relative imports then resolve between the files exactly as in a browser.

import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { constants, Script } from 'node:vm';

export interface Bundle {
  entryUrl: string;
  // Absolute URL -> source text, for the entry and every chunk reachable from it.
  files: Map<string, string>;
}

export interface RunningBundle {
  dir: string;
  dispose: () => Promise<void>;
}

// A relative .js specifier after `from` or `import` (static, side-effect-only or dynamic). Matching on those
// keywords keeps a string like "./README.js" in application text from being taken for a chunk.
const SPECIFIER = /(?:\bfrom|\bimport)\s*\(?\s*["'`](\.{1,2}\/[\w./-]+\.js)["'`]/g;

const describe = (e: unknown) => (e instanceof Error ? `${e.name}: ${e.message}` : String(e));

// Vitest's module runner would transform a file fetched from the site (and a plain `new Function` has no import
// callback inside its vm context), so reach Node's own dynamic import through a script that asks for the default loader.
const nativeImport = new Script('(url) => import(url)', {
  importModuleDynamically: constants.USE_MAIN_CONTEXT_DEFAULT_LOADER,
}).runInThisContext() as (url: string) => Promise<unknown>;

// The entry plus every chunk it reaches through relative imports. Chunks are same-origin by construction: a
// relative specifier cannot leave the origin of the file that names it. Fetches run in order; there are few.
export async function fetchChunks(entryUrl: string, entryText: string, fetchText: (url: string) => Promise<string>): Promise<Bundle> {
  const files = new Map([[entryUrl, entryText]]);
  const pending = [entryUrl];
  for (let url = pending.shift(); url !== undefined; url = pending.shift()) {
    for (const [, specifier] of (files.get(url) ?? '').matchAll(SPECIFIER)) {
      const chunkUrl = new URL(specifier, url).href;
      if (files.has(chunkUrl)) continue;
      try {
        files.set(chunkUrl, await fetchText(chunkUrl));
      } catch (e) {
        throw new Error(`Could not fetch chunk ${chunkUrl}: ${describe(e)}`, { cause: e });
      }
      pending.push(chunkUrl);
    }
  }
  return { entryUrl, files };
}

// Writes the bundle to a temp directory and imports the entry (which starts the app) and then every chunk, so
// a chunk the entry only reaches later (a lazy import) still has to load. A failure names the file it came from.
export async function runBundle({ entryUrl, files }: Bundle): Promise<RunningBundle> {
  const dir = await mkdtemp(join(tmpdir(), 'hdt-bundle-'));
  const dispose = () => rm(dir, { recursive: true, force: true });
  const pathOf = (url: string) => join(dir, new URL(url).pathname);
  try {
    // So Node reads the .js files as ES modules.
    await writeFile(join(dir, 'package.json'), '{"type":"module"}');
    for (const [url, text] of files) {
      await mkdir(dirname(pathOf(url)), { recursive: true });
      await writeFile(pathOf(url), text);
    }
    for (const url of [entryUrl, ...[...files.keys()].filter((u) => u !== entryUrl)]) {
      try {
        await nativeImport(pathToFileURL(pathOf(url)).href);
      } catch (e) {
        throw new Error(`Could not run ${url === entryUrl ? 'entry script' : 'chunk'} ${url}: ${describe(e)}`, { cause: e });
      }
    }
  } catch (e) {
    await dispose();
    throw e;
  }
  return { dir, dispose };
}
