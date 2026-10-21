// Signs in the funded Supabase test user and prints its access token and account id as one JSON
// line on stdout - the hand-off to android/test-weekly.ps1 (#75), which gives the token to the
// instrumented External suite and makes the account id its RevenueCat customer. Run it as
// `npm run --silent live-token`. Credentials come from liveToken.ts (environment, then
// web/.env.local); a missing or rejected one exits 1 with the reason on stderr. Only the token and
// account id reach stdout, and nothing else is ever printed.
import { fileURLToPath } from "node:url";
import { readEnvFile, signInTestAccount, subjectOf } from "./liveToken.ts";

export type FundedSession = { accessToken: string; accountId: string };

export async function fundedSession(
  env: Record<string, string | undefined> = process.env,
  fileValues: Record<string, string> = readEnvFile(),
): Promise<FundedSession> {
  const accessToken = await signInTestAccount("funded", env, fileValues);
  return { accessToken, accountId: subjectOf(accessToken) };
}

export async function runCli(
  writeOut: (line: string) => void,
  writeErr: (line: string) => void,
  env: Record<string, string | undefined> = process.env,
  fileValues: Record<string, string> = readEnvFile(),
): Promise<number> {
  try {
    writeOut(JSON.stringify(await fundedSession(env, fileValues)));
    return 0;
  } catch (error) {
    writeErr(error instanceof Error ? error.message : "sign-in failed");
    return 1;
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  process.exitCode = await runCli(console.log, console.error);
}
