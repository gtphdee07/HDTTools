// Runs the External suite via `node --test`, narrowed to the surfaces the wrapper passes
// in EXTERNAL_SURFACES (comma-separated) by matching each test name's "[surface]" tag.
// Unset runs every external test. When the wrapper sets EXTERNAL_RESULTS_FILE, a JUnit report
// goes there too so it can record each surface from its own tests (ADR-0008).
import { spawnSync } from "node:child_process";

const surfaces = (process.env.EXTERNAL_SURFACES ?? "").split(",").filter(Boolean);
const resultsFile = process.env.EXTERNAL_RESULTS_FILE;
const args = ["--test"];
if (resultsFile) {
  args.push("--test-reporter=spec", "--test-reporter-destination=stdout");
  args.push("--test-reporter=junit", `--test-reporter-destination=${resultsFile}`);
}
if (surfaces.length > 0) args.push(`--test-name-pattern=\\[(${surfaces.join("|")})\\]`);
args.push("src/external/*.external.test.ts");

process.exit(spawnSync(process.execPath, args, { stdio: "inherit" }).status ?? 1);
