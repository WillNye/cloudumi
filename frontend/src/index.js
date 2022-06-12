import React from 'react'
import ReactDOM from 'react-dom'
import * as Sentry from '@sentry/react'
import { BrowserTracing } from '@sentry/tracing'
import 'semantic-ui-css/semantic.min.css'
import './index.css'
import App from './App'
import * as serviceWorker from './serviceWorker'

if (process.env.FRONTEND_SENTRY_DSN) {
  Sentry.init({
    dsn: process.env.FRONTEND_SENTRY_DSN,
    integrations: [new BrowserTracing()],

    // Set tracesSampleRate to 1.0 to capture 100%
    // of transactions for performance monitoring.
    // We recommend adjusting this value in production
    tracesSampleRate: 1.0,
  })
}

ReactDOM.render(<App />, document.getElementById('root'))

// If you want your app to work offline and load faster, you can change
// unregister() to register() below. Note this comes with some pitfalls.
// Learn more about service workers: https://bit.ly/CRA-PWA
if (!process.env.NODE_ENV || process.env.NODE_ENV === 'development') {
  // dev code
  serviceWorker.unregister()
} else {
  // production code
  serviceWorker.register()
}
