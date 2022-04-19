/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect } from 'react'
import { Menu, Header } from 'semantic-ui-react'

export const SidebarMenu = ({
  headerTitle,
  menuItems,
  activeItem,
  onClickItem,
  onChangeActive,
}) => {

  useEffect(() => {
    const active = menuItems?.filter(({ name }) => name === activeItem)?.[0]
    if (active) onChangeActive(active)
  }, [activeItem])

  const header = headerTitle && (
    <Menu.Header>
      <Header as='h2'>{headerTitle}</Header>
    </Menu.Header>
  )

  const items =
    menuItems &&
    menuItems.map(({ name, label, Component }) => (
      <Menu.Item
        key={name}
        name={name}
        content={label}
        active={activeItem === name}
        onClick={(_, { name }) => {
          onClickItem({ name, label, Component })
        }}
      />
    ))

  return (
    <Menu pointing secondary vertical>
      {header}
      {items}
    </Menu>
  )
}
