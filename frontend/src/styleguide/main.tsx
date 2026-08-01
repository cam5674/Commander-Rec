import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '../styles/tokens.css';
import { StyleGuidePage } from './StyleGuidePage';

createRoot(document.getElementById('styleguide-root')!).render(
  <StrictMode>
    <StyleGuidePage />
  </StrictMode>,
);
