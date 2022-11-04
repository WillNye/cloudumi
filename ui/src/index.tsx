import React from 'react';
import ReactDOM from 'react-dom/client';
import { Helmet, HelmetProvider } from 'react-helmet-async';
import { BrowserRouter } from 'react-router-dom';

// Note: Order is important here
import 'core/utils/tracking';

import { ErrorBoundary } from 'shared/utils/ErrorBoundary';
import { Auth } from 'core/Auth';
import { ApolloProvider } from 'core/Apollo';
import { App } from './App';

import './index.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <ApolloProvider>
        <HelmetProvider>
          <Helmet titleTemplate="%s | NOQ" defaultTitle="NOQ" />
          <ErrorBoundary>
            <Auth>
              <App />
            </Auth>
          </ErrorBoundary>
        </HelmetProvider>
      </ApolloProvider>
    </BrowserRouter>
  </React.StrictMode>
);
