import { ServerError } from '@apollo/client';
import { onError } from '@apollo/client/link/error';
import * as Sentry from '@sentry/browser';

export const errorLink = navigate =>
  onError(({ graphQLErrors, networkError }) => {
    if (graphQLErrors) {
      graphQLErrors.forEach(({ message, locations, path }) => {
        console.error(
          `[GraphQL error]: Message: ${message}, Location: ${locations}, Path: ${path}`
        );

        if (import.meta.env.PROD) {
          // Let's add some additional scope for tracking
          Sentry.withScope(scope => {
            scope.setTag('type', 'graphql');
            scope.setTag('path', path as any);
            scope.setExtra('locations', locations);
            Sentry.captureException(new Error(message));
          });
        }
      });
    }

    if (networkError) {
      console.error(`[Network error]: ${networkError}`);

      // If we get a 401, let's redirect to the login page
      if ((networkError as ServerError).statusCode === 401) {
        navigate('/login');
      }
    }
  });
