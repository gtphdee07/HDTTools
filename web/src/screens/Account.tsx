import { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuth } from '../auth';
import type { ActionResult } from '../auth';
import { Button } from '../design-system/Button';
import { Card } from '../design-system/Card';

type Mode = 'signin' | 'signup' | 'reset';

const inputStyle: React.CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  padding: '10px 12px',
  marginTop: 4,
  fontSize: 14,
  border: '1px solid var(--border-subtle)',
  borderRadius: 'var(--radius-md)',
};

const linkStyle: React.CSSProperties = {
  background: 'none',
  border: 'none',
  color: 'var(--accent-secondary-hover)',
  cursor: 'pointer',
  padding: 0,
  fontSize: 13,
  textDecoration: 'underline',
};

interface AccountProps {
  onDone: () => void;
}

export function Account({ onDone }: AccountProps) {
  const auth = useAuth();
  const [mode, setMode] = useState<Mode>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async (action: () => Promise<ActionResult>, success?: string) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    const result = await action();
    setBusy(false);
    if (result.error) setError(result.error);
    else if (result.needsConfirmation) setNotice('Check your email to confirm your account, then sign in.');
    else if (success) setNotice(success);
  };

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
    setNotice(null);
  };

  if (!auth.configured) {
    return (
      <Card title="Accounts unavailable" subtitle="Sign-in is not set up on this site. The free calculator still works without an account." />
    );
  }

  if (auth.loading) return <Card title="Loading account..." />;

  if (auth.recovering) {
    const submit = (e: FormEvent) => {
      e.preventDefault();
      void run(() => auth.updatePassword(password), 'Password updated.');
    };
    return (
      <Card title="Choose a new password">
        <form onSubmit={submit} style={{ marginTop: 12 }}>
          <label style={{ fontSize: 13 }}>
            New password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} style={inputStyle} />
          </label>
          <Feedback error={error} notice={notice} />
          <Button type="submit" disabled={busy} style={{ marginTop: 12 }}>
            Update password
          </Button>
        </form>
      </Card>
    );
  }

  if (auth.user) {
    return (
      <Card title="Your account" subtitle={`Signed in as ${auth.user.email ?? auth.user.id}`}>
        <Feedback error={error} notice={notice} />
        <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
          <Button variant="secondary" disabled={busy} onClick={() => void run(() => auth.signOut())}>
            Sign out
          </Button>
          <Button variant="ghost" onClick={onDone}>
            Back to Dashboard
          </Button>
        </div>
      </Card>
    );
  }

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (mode === 'signin') void run(() => auth.signIn(email, password));
    else if (mode === 'signup') void run(() => auth.signUp(email, password));
    else void run(() => auth.requestPasswordReset(email), 'Check your email for a password reset link.');
  };

  const title = mode === 'signin' ? 'Sign in' : mode === 'signup' ? 'Create account' : 'Reset password';

  return (
    <Card title={title} subtitle="An account is only needed for paid features. The free calculator needs no account.">
      <form onSubmit={submit} style={{ marginTop: 12 }}>
        <label style={{ fontSize: 13 }}>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required style={inputStyle} />
        </label>
        {mode !== 'reset' && (
          <label style={{ fontSize: 13, display: 'block', marginTop: 10 }}>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} style={inputStyle} />
          </label>
        )}
        <Feedback error={error} notice={notice} />
        <Button type="submit" disabled={busy} style={{ marginTop: 12 }}>
          {mode === 'signin' ? 'Sign in' : mode === 'signup' ? 'Create account' : 'Send reset link'}
        </Button>
      </form>
      <div style={{ display: 'flex', gap: 16, marginTop: 14 }}>
        {mode !== 'signin' && (
          <button style={linkStyle} onClick={() => switchMode('signin')}>
            Back to sign in
          </button>
        )}
        {mode !== 'signup' && (
          <button style={linkStyle} onClick={() => switchMode('signup')}>
            Create an account
          </button>
        )}
        {mode === 'signin' && (
          <button style={linkStyle} onClick={() => switchMode('reset')}>
            Forgot password?
          </button>
        )}
      </div>
    </Card>
  );
}

function Feedback({ error, notice }: { error: string | null; notice: string | null }) {
  return (
    <>
      {error && (
        <div role="alert" style={{ color: 'var(--color-danger, #b00020)', fontSize: 13, marginTop: 10 }}>
          {error}
        </div>
      )}
      {notice && (
        <div role="status" style={{ fontSize: 13, marginTop: 10 }}>
          {notice}
        </div>
      )}
    </>
  );
}
