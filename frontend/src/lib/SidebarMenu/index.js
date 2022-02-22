import React, { useEffect } from 'react';
import { Menu, Header } from 'semantic-ui-react';

export const SidebarMenu = ({
  headerTitle,
  menuItems,
  activeItem,
  onClickItem = () => {},
  onChangeActive = () => {} 
}) => {

  useEffect(() => {
    onChangeActive(activeItem);
  }, [activeItem, onChangeActive]);

  const header = headerTitle && (
    <Menu.Header>
      <Header as="h2">{headerTitle}</Header>
    </Menu.Header>
  );

  const items = menuItems && (
    menuItems.map(({ name, label, ...rest }) => (
      <Menu.Item
        key={name}
        name={name}
        content={label}
        active={activeItem === name}
        onClick={(_, { name }) => onClickItem({ name, label, ...rest })}
      />
    ))
  );

  return (
    <Menu pointing secondary vertical>
      {header}
      {items}
    </Menu>
  );

};
