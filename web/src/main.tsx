import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './design-system/tokens.css';
import App from './App.tsx';
import { AuthProvider, createSupabaseAuthClient } from './auth';
import { BillingProvider, createRevenueCatClientFromEnv } from './billing';
import { GarageProvider } from './garage';
import { getSupabaseClient } from './supabaseClient';
import { createSupabaseGarageBackend } from './supabaseGarage';

const authClient = createSupabaseAuthClient();
const billingClient = createRevenueCatClientFromEnv();
const supabase = getSupabaseClient();
const garageBackend = supabase ? createSupabaseGarageBackend(supabase) : null;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider client={authClient}>
      <BillingProvider client={billingClient}>
        <GarageProvider backend={garageBackend}>
          <App />
        </GarageProvider>
      </BillingProvider>
    </AuthProvider>
  </StrictMode>,
);
