// Test-entry guard: stops the proxy's tests early, with a plain instruction, when
// `npm install` was never run here (node_modules is gitignored, so a fresh git worktree
// has none). Without it the missing Claude SDK only surfaces when scan.ts lazily loads
// it, which the service reports as a refunded 502 `extraction_failed` - indistinguishable
// from a real extraction failure. Nothing in the shipped Worker imports this file.
import { readFileSync } from "node:fs";
import { join } from "node:path";

type Resolve = (specifier: string) => string;

function packageDependencies(): Record<string, string> {
  const raw = readFileSync(join(import.meta.dirname, "..", "package.json"), "utf8");
  return (JSON.parse(raw) as { dependencies?: Record<string, string> }).dependencies ?? {};
}

export function missingDependencies(
  dependencies: Record<string, string> = packageDependencies(),
  resolve: Resolve = (specifier) => import.meta.resolve(specifier),
): string[] {
  return Object.keys(dependencies).filter((name) => {
    try {
      resolve(name);
      return false;
    } catch {
      return true;
    }
  });
}

export function installMessage(missing: string[]): string {
  return [
    `The scan proxy's dependencies are not installed (missing: ${missing.join(", ")}).`,
    "Run `npm install` in workers/scan-proxy, or from the repo root:",
    "  npm --prefix workers/scan-proxy install",
    "then run the tests again.",
  ].join("\n");
}

export function assertInstalled(): void {
  const missing = missingDependencies();
  if (missing.length > 0) throw new Error(installMessage(missing));
}
