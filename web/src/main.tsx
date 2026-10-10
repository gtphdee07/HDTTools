import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './design-system/tokens.css';
import App from './App.tsx';
import { AuthProvider, createSupabaseAuthClient } from './auth';
import { BillingProvider, createRevenueCatClientFromEnv } from './billing';

const authClient = createSupabaseAuthClient();
const billingClient = createRevenueCatClientFromEnv();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider client={authClient}>
      <BillingProvider client={billingClient}>
        <App />
      </BillingProvider>
    </AuthProvider>
  </StrictMode>,
);
