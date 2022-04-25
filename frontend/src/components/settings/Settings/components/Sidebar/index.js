import React from 'react'
import { SidebarMenu } from 'lib/SidebarMenu'
import { general, services } from './content'

export const Sidebar = ({ onClickItem, activeItem, onItemChange }) => {
  return (
    <>
      <SidebarMenu
        headerTitle='Services'
        menuItems={services}
        onClickItem={onClickItem}
        activeItem={activeItem}
        onChangeActive={onItemChange}
      />

      <SidebarMenu
        headerTitle='General'
        menuItems={general}
        onClickItem={onClickItem}
        activeItem={activeItem}
        onChangeActive={onItemChange}
      />
    </>
  )
}
