// The tester kit's two public values, in one place: the address testers send feedback to, and the
// address of the Web app itself. docs/BETA_TESTER_GUIDE.md names both, and betaGuide.test.ts fails if
// the guide and these constants drift apart (Android's feedback link is checked against the guide).
export const FEEDBACK_EMAIL = 'WTIAppDev@gmail.com';
export const FEEDBACK_MAILTO = `mailto:${FEEDBACK_EMAIL}?subject=${encodeURIComponent('RigCheck feedback')}`;
export const WEB_ADDRESS = 'https://rigcheck-web.pages.dev';

// True only when the build sets VITE_BETA=true (web/.env.production); a production build drops the
// "Beta: test payments" label by deleting that one line. Read at call time so a test can set it.
export function isBeta(): boolean {
  return import.meta.env.VITE_BETA === 'true';
}
