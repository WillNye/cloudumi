import React from 'react'
import ReactDOM from 'react-dom'
import * as Sentry from '@sentry/react'
import { BrowserTracing } from '@sentry/tracing'
import 'semantic-ui-css/semantic.min.css'
import './index.css'
import App from './App'
import * as serviceWorker from './serviceWorker'
;(function () {
  if (!process.env.NODE_EXTRA_CA_CERTS) return
  try {
    var extraca = require('fs').readFileSync(process.env.NODE_EXTRA_CA_CERTS)
  } catch (e) {
    return
  }

  var NativeSecureContext = process.binding('crypto').SecureContext
  var oldaddRootCerts = NativeSecureContext.prototype.addRootCerts
  NativeSecureContext.prototype.addRootCerts = function () {
    var ret = oldaddRootCerts.apply(this, arguments)
    this.addCACert(extraca)
    return ret
  }
})()

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
