import React, { useState } from 'react'
import { Screen } from 'lib/Screen'
import { ServiceAWS } from './components/ServiceAWS'
import { Sidebar } from './components/Sidebar'
import { useHistory } from 'react-router-dom'

export const Settings = (props) => {
  const defaultActiveItem = { name: 'aws', Component: ServiceAWS }

  const history = useHistory()

  const [{ name: activeItem, Component }, setActiveItem] =
    useState(defaultActiveItem)

  const handleItemChange = (active) => {
    // Update route pathname
  }

  // console.log(history, props)

  const renderComponent = Component ? <Component /> : null

  return (
    <Screen
      renderSidebar={
        <Sidebar
          activeItem={activeItem}
          setActiveItem={setActiveItem}
          handleItemChange={handleItemChange}
        />
      }
    >
      {renderComponent}
    </Screen>
  )
}
