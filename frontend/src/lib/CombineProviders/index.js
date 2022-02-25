import React from 'react'

export const CombinedProviders = (providers) => {
  const Providers = providers.reduce(
    (AccumulatedProvider, Current) => {
      return ({ children }) => {
        return (
          <AccumulatedProvider>
            <Current>{children}</Current>
          </AccumulatedProvider>
        )
      }
    },
    ({ children }) => children
  )
  return Providers
}
