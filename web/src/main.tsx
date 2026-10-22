import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './design-system/tokens.css';
import App from './App.tsx';
import { AuthProvider, createSupabaseAuthClient } from './auth';
import { BillingProvider, createRevenueCatClientFromEnv } from './billing';
import { GarageProvider } from './garage';
import { HistoryProvider } from './history';
import { getSupabaseClient } from './supabaseClient';
import { createSupabaseGarageBackend } from './supabaseGarage';
import { createSupabaseHistoryBackend } from './supabaseHistory';

const authClient = createSupabaseAuthClient();
const billingClient = createRevenueCatClientFromEnv();
const supabase = getSupabaseClient();
const garageBackend = supabase ? createSupabaseGarageBackend(supabase) : null;
const historyBackend = supabase ? createSupabaseHistoryBackend(supabase) : null;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider client={authClient}>
      <BillingProvider client={billingClient}>
        <GarageProvider backend={garageBackend}>
          <HistoryProvider backend={historyBackend}>
            <App />
          </HistoryProvider>
        </GarageProvider>
      </BillingProvider>
    </AuthProvider>
  </StrictMode>,
);
