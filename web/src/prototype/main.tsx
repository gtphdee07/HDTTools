// THROWAWAY PROTOTYPE entry point — see PrototypeCheckout.tsx.
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { PrototypeCheckout } from './PrototypeCheckout.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PrototypeCheckout />
  </StrictMode>,
);
