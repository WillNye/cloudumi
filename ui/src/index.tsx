import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker';
import cssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker';
import htmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker';
import tsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker';
import YamlWorker from './yaml.worker.js?worker';

self.MonacoEnvironment = {
  getWorker(_, label) {
    if (label === 'json') {
      return new jsonWorker();
    }
    if (label === 'css' || label === 'scss' || label === 'less') {
      return new cssWorker();
    }
    if (label === 'html' || label === 'handlebars' || label === 'razor') {
      return new htmlWorker();
    }
    if (label === 'typescript' || label === 'javascript') {
      return new tsWorker();
    }
    if (label === 'yaml' || label === 'yml') {
      return new YamlWorker();
    }
    return new editorWorker();
  }
};

import React from 'react';
import ReactDOM from 'react-dom/client';
import { Helmet, HelmetProvider } from 'react-helmet-async';
import { BrowserRouter } from 'react-router-dom';
import { DesignTokensProvider } from 'reablocks';
import { Mode, applyMode } from '@cloudscape-design/global-styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Note: Order is important here
import 'core/utils/tracking';

import { theme } from 'shared/utils/DesignTokens';
import { ErrorBoundary } from 'shared/utils/ErrorBoundary';
import { Auth } from 'core/Auth';
import { App } from './App';
import favicon from './assets/brand/favicon.ico';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false
    }
  }
});

applyMode(Mode.Dark);

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      {/* <ApolloProvider> */}
      <QueryClientProvider client={queryClient}>
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
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>
);
