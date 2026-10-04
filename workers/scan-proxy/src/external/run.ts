// Runs the External suite via `node --test`, narrowed to the surfaces the wrapper passes
// in EXTERNAL_SURFACES (comma-separated) by matching each test name's "[surface]" tag.
// Unset runs every external test.
import { spawnSync } from "node:child_process";

const surfaces = (process.env.EXTERNAL_SURFACES ?? "").split(",").filter(Boolean);
const args = ["--test"];
if (surfaces.length > 0) args.push(`--test-name-pattern=\\[(${surfaces.join("|")})\\]`);
args.push("src/external/*.external.test.ts");

process.exit(spawnSync(process.execPath, args, { stdio: "inherit" }).status ?? 1);
