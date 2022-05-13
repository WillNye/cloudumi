import React, { useState } from 'react'
import { Screen } from 'lib/Screen'
import { Sidebar } from './components/Sidebar'
import { useHistory } from 'react-router-dom'
import { ServiceAWS } from './components/ServiceAWS'
import './Settings.css'

export const Settings = ({ computedMatch, origin }) => {
  const { push } = useHistory()

  const { tabName } = computedMatch?.params

  const defaultActiveItem = { name: 'aws', Component: ServiceAWS }

  const [{ Component }, setActiveItem] = useState(defaultActiveItem)

  const handleItemClick = ({ name }) => {
    push(origin + '/' + name)
  }

  const handleItemChange = ({ name, Component }) => {
    setActiveItem({ name, Component })
  }

  return (
    <Screen
      renderSidebar={
        <Sidebar
          activeItem={tabName}
          onClickItem={handleItemClick}
          onItemChange={handleItemChange}
          handleItemChange={handleItemChange}
        />
      }
    >
      {Component ? <Component /> : null}
    </Screen>
  )
}
