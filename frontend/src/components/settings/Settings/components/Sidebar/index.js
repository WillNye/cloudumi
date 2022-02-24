import React from 'react'
import { SidebarMenu } from 'lib/SidebarMenu'
import { general, services } from './content'

export const Sidebar = ({ setActiveItem, activeItem, handleItemChange }) => {
  return (
    <>
      <SidebarMenu
        headerTitle='Services'
        menuItems={services}
        onClickItem={setActiveItem}
        activeItem={activeItem}
        onChangeActive={handleItemChange}
      />

      <SidebarMenu
        headerTitle='General'
        menuItems={general}
        onClickItem={setActiveItem}
        activeItem={activeItem}
        onChangeActive={handleItemChange}
      />
    </>
  )
}
