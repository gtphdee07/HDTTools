import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './design-system/tokens.css';
import App from './App.tsx';
import { AuthProvider, createSupabaseAuthClient } from './auth';

const authClient = createSupabaseAuthClient();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider client={authClient}>
      <App />
    </AuthProvider>
  </StrictMode>,
);
