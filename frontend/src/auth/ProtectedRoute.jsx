import React, { useEffect } from 'react'
import { useAuth } from './AuthProviderDefault'
import { useNotifications } from '../components/hooks/notifications'
import { Route, useHistory, useLocation, useRouteMatch } from 'react-router-dom'
import ReactGA from 'react-ga'

const ProtectedRoute = (props) => {
  const auth = useAuth()
  const notifications = useNotifications()
  let history = useHistory()
  const location = useLocation()
  const { login, user, isSessionExpired } = auth
  const { RetrieveNotificationsAtInterval } = notifications
  const match = useRouteMatch(props)
  const { component: Component, ...rest } = props

  useEffect(() => {
    // make sure we only handle the registered routes
    if (!match) {
      return
    }

    // TODO(heewonk), This is a temporary way to prevent multiple logins when 401 type of access deny occurs.
    // Revisit later to enable this logic only when ALB type of authentication is being used.
    if (isSessionExpired) {
      return
    }

    if (!user) {
      ;(async () => {
        await login(history)
      })()
    }
    if (user) {
      let interval = 60
      if (user?.site_config?.notifications?.request_interval) {
        interval = user.site_config.notifications.request_interval
      }
      RetrieveNotificationsAtInterval(interval)
    }
  }, [match, user, isSessionExpired, login, history]) // eslint-disable-line

  if (!user) {
    return null
  }

  if (user?.google_analytics_initialized) {
    const currentPath = location.pathname + location.search
    ReactGA.set({ page: currentPath })
    ReactGA.set({ domainName: '.noq.dev' })
    ReactGA.pageview(currentPath)
  }

  if (window?.clarity) {
    window.clarity('stop')
    window.clarity('start')
  }

  if (window?.dataLayer && window?.dataLayer?.push) {
    window.dataLayer.push({
      event: 'event',
      eventProps: {
        email: user?.user,
      },
    })
  }
  return (
    <Route
      {...rest}
      render={(props) => {
        return <Component {...props} {...rest} {...auth} />
      }}
    />
  )
}

export default ProtectedRoute
