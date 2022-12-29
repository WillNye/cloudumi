import React from 'react';
import ReactDOM from 'react-dom/client';
import { Helmet, HelmetProvider } from 'react-helmet-async';
import { BrowserRouter } from 'react-router-dom';
import { DesignTokensProvider } from 'reablocks';

// Note: Order is important here
import 'core/utils/tracking';

import { theme } from 'shared/utils/DesignTokens';
import { ErrorBoundary } from 'shared/utils/ErrorBoundary';
import { Auth } from 'core/Auth';
import { ApolloProvider } from 'core/Apollo';
import { App } from './App';
import favicon from './assets/brand/favicon.ico';

import './index.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      {/* <ApolloProvider> */}
      <HelmetProvider>
        <Helmet titleTemplate="%s | Noq" defaultTitle="Noq">
          <link rel="icon" type="image/svg+xml" href={favicon} />
        </Helmet>
        <DesignTokensProvider value={theme}>
          <ErrorBoundary>
            <Auth>
              <App />
            </Auth>
          </ErrorBoundary>
        </DesignTokensProvider>
      </HelmetProvider>
      {/* </ApolloProvider> */}
    </BrowserRouter>
  </React.StrictMode>
);
