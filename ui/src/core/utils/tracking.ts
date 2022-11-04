import * as Sentry from '@sentry/react';
import { BrowserTracing } from '@sentry/tracing';

// Add in sentry if not running on local
if (import.meta.env.PROD) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    autoSessionTracking: true,
    integrations: [
      new BrowserTracing()
    ],
    // release: ADD_VERSION_HERE,
    // tracesSampleRate: ENV === 'dev' ? 1.0 : 0.25,
    // environment: ADD_ENV_HERE
  });
}
