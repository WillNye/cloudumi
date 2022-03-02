import React from 'react'

import { ScreenContainer, ScreenContent, ScreenSidebar } from './styles'

export const Screen = ({ children, renderSidebar }) => {
  const sidebar = renderSidebar && (
    <ScreenSidebar>{renderSidebar}</ScreenSidebar>
  )

  return (
    <ScreenContainer>
      {sidebar}
      <ScreenContent>{children}</ScreenContent>
    </ScreenContainer>
  )
}
