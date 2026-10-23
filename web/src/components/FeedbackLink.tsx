import { FEEDBACK_MAILTO } from '../betaKit';

// A mailto link to the owner's feedback address; the footer and the Account screen both show it.
export function FeedbackLink() {
  return (
    <a href={FEEDBACK_MAILTO} style={{ color: 'var(--fg-1)', fontWeight: 500 }}>
      Send feedback
    </a>
  );
}
