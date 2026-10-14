import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import App from './App';
import { AuthProvider } from './auth';
import type { AuthClient, AuthSession } from './auth';
import { BillingProvider } from './billing';
import type { BillingClient } from './billing';

// Test kit for driving the real screens against a fake Scan service. The fake follows the contract the
// Worker keeps (workers/scan-proxy README): the account token names who is charged, the charge comes
// before the extraction, a failed extraction is refunded, and the same request id from the same account
// and photo is charged once. Whether the Worker really does is proven by its own tests; here the fake
// stands in so the Web side can be proven to send what that contract needs and to show what comes back.

const SERVICE_URL = 'https://scan.example.com';
const PAT: AuthSession = { access_token: 'token-pat', user: { id: 'acct-pat', email: 'pat@example.com' } };

function makeAuth(session: AuthSession | null = PAT): AuthClient {
  return {
    getSession: vi.fn(async () => ({ data: { session }, error: null })),
    onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: () => {} } } })),
    signUp: vi.fn(),
    signInWithPassword: vi.fn(),
    signOut: vi.fn(),
    resetPasswordForEmail: vi.fn(),
    updateUser: vi.fn(),
  } as unknown as AuthClient;
}

interface ScanRequestSeen {
  authorization: string | null;
  docType: string;
  mediaType: string;
  clientRequestId: string | undefined;
}

// 'fail' is an extraction that failed and was refunded; 'fail-no-refund' one whose refund failed too.
type Extraction = { fields: Record<string, unknown> } | 'fail' | 'fail-no-refund';

export interface FakeWorld {
  billing: BillingClient;
  fetch: ReturnType<typeof vi.fn>;
  // Every request that reached the service, in order.
  requests: ScanRequestSeen[];
  balance(): number;
  // What the next extractions return, in order; after they run out, every extraction reads { manufacturer: 'Ford' }.
  queueExtraction(...results: Extraction[]): void;
  // The next request is processed by the service but its answer never reaches the browser.
  loseNextResponse(): void;
  // The balance changes behind the app's back, as another device spending would.
  setBalance(balance: number): void;
  // The next request is charged and processed, but its answer is held until the returned function is called,
  // so a scan stays in flight for as long as a test needs it to.
  holdNextResponse(): () => void;
}

export function makeWorld({ isPro = true, balance = 3 }: { isPro?: boolean; balance?: number } = {}): FakeWorld {
  let current = balance;
  const chargedKeys = new Set<string>();
  const queue: Extraction[] = [];
  const requests: ScanRequestSeen[] = [];
  let loseNext = false;
  let holdNext: Promise<void> | null = null;

  const answer = (status: number, body: unknown) => ({ ok: status < 300, status, json: async () => body });

  const handleRequest = (init: RequestInit) => {
    const headers = init.headers as Record<string, string>;
    const body = JSON.parse(String(init.body));
    requests.push({
      authorization: headers.Authorization ?? null,
      docType: body.doc_type,
      mediaType: body.media_type,
      clientRequestId: body.client_request_id,
    });
    if (headers.Authorization !== `Bearer ${PAT.access_token}`) return answer(401, { ok: false, code: 'unauthorized' });

    const key = [headers.Authorization, body.doc_type, body.media_type, body.image_base64, body.client_request_id].join('|');
    if (!chargedKeys.has(key)) {
      if (current < 1) return answer(402, { ok: false, code: 'insufficient_credits' });
      current -= 1;
      chargedKeys.add(key);
    }
    const extraction = queue.shift() ?? { fields: { manufacturer: 'Ford' } };
    if (extraction === 'fail-no-refund') return answer(502, { ok: false, code: 'extraction_failed_no_refund' });
    if (extraction === 'fail') {
      current += 1;
      return answer(502, { ok: false, code: 'extraction_failed' });
    }
    return answer(200, { ok: true, doc_type: body.doc_type, fields: extraction.fields });
  };

  const fetchFake = vi.fn(async (url: string, init: RequestInit) => {
    if (url !== `${SERVICE_URL}/v1/scan`) throw new Error(`unexpected request to ${url}`);
    const response = handleRequest(init);
    if (holdNext) {
      const held = holdNext;
      holdNext = null;
      await held;
    }
    if (loseNext) {
      loseNext = false;
      throw new TypeError('Failed to fetch');
    }
    return response;
  });

  const billing = {
    identify: vi.fn(async () => {}),
    getProOffer: vi.fn(async () => ({ price: '$9.99' })),
    getStatus: vi.fn(async () => ({ isPro, scanBalance: current })),
    getScanPacks: vi.fn(async () => [{ id: 'pack_10', title: '10 scans', price: '$2.99' }]),
    purchasePro: vi.fn(),
    purchaseScanPack: vi.fn(),
  } as unknown as BillingClient;

  return {
    billing,
    fetch: fetchFake,
    requests,
    balance: () => current,
    queueExtraction: (...results) => void queue.push(...results),
    loseNextResponse: () => {
      loseNext = true;
    },
    setBalance: (next) => {
      current = next;
    },
    holdNextResponse: () => {
      let release = () => {};
      holdNext = new Promise<void>((resolve) => {
        release = resolve;
      });
      return release;
    },
  };
}

export function renderApp({ world, session = PAT }: { world: FakeWorld | null; session?: AuthSession | null }) {
  vi.stubGlobal('fetch', world?.fetch ?? vi.fn());
  vi.stubEnv('VITE_SCAN_SERVICE_URL', SERVICE_URL);
  render(
    <AuthProvider client={makeAuth(session)}>
      <BillingProvider client={world?.billing ?? null}>
        <App />
      </BillingProvider>
    </AuthProvider>,
  );
  return userEvent.setup();
}

type User = ReturnType<typeof userEvent.setup>;

export const photo = (name = 'truck.jpg') => new File([`pixels of ${name}`], name, { type: 'image/jpeg' });
export const fileInput = () => document.querySelector('input[type="file"]') as HTMLInputElement;

export async function startNewRig(user: User, nickname = 'Big Blue') {
  await user.click(screen.getAllByRole('button', { name: 'Start New Check' })[0]);
  await user.type(screen.getByPlaceholderText('e.g. Big Blue'), nickname);
  await user.click(screen.getByRole('button', { name: 'Start New Rig' }));
}

export async function chooseAndExtract(user: User, file = photo()) {
  await user.upload(fileInput(), file);
  await user.click(screen.getByRole('button', { name: 'Extract Data' }));
}

// Renders the app signed in and starts a check on the Truck Tag photo step, with the balance read (3 scans).
export async function reachTruckUpload(world: FakeWorld) {
  const user = renderApp({ world });
  await startNewRig(user);
  await screen.findByText(/3 scans left/);
  return user;
}
