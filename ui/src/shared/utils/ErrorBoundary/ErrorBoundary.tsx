import React, { useCallback, FC } from 'react';
import { ErrorComponent } from './ErrorComponent';
import { ErrorBoundary as ReactErrorBoundary } from 'react-error-boundary';

export const ErrorBoundary: FC<{ children: React.ReactNode }> = ({
  children
}) => {
  const onError = useCallback((error: Error) => {
    if (import.meta.env.PROD) {
      // TODO: Add Sentry or other error reporting service
    }
  }, []);

  return (
    <ReactErrorBoundary FallbackComponent={ErrorComponent} onError={onError}>
      {children}
    </ReactErrorBoundary>
  );
};
