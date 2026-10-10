import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './design-system/tokens.css';
import App from './App.tsx';
import { AuthProvider, createSupabaseAuthClient } from './auth';
import { GarageProvider } from './garage';
import { getSupabaseClient } from './supabaseClient';
import { createSupabaseGarageBackend } from './supabaseGarage';

const authClient = createSupabaseAuthClient();
const supabase = getSupabaseClient();
const garageBackend = supabase ? createSupabaseGarageBackend(supabase) : null;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider client={authClient}>
      <GarageProvider backend={garageBackend}>
        <App />
      </GarageProvider>
    </AuthProvider>
  </StrictMode>,
);
