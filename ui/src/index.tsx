import React from 'react';
import ReactDOM from 'react-dom/client';
import { Helmet, HelmetProvider } from 'react-helmet-async';
import { BrowserRouter } from 'react-router-dom';

import { ErrorBoundary } from 'shared/utils/ErrorBoundary';
import { Auth } from 'core/Auth';
import { App } from './App';

import './index.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <HelmetProvider>
        <Helmet titleTemplate="%s | NOQ" defaultTitle="NOQ" />
        <ErrorBoundary>
          <Auth>
            <App />
          </Auth>
        </ErrorBoundary>
      </HelmetProvider>
    </BrowserRouter>
  </React.StrictMode>
);
