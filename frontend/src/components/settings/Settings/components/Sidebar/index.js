import React from 'react';
import { SidebarMenu } from '../../../../../lib/SidebarMenu';
import ServiceAWS from './../ServiceAWS';

const Sidebar = ({ setActiveItem, activeItem, handleItemChange }) => {

  return (
    <>

      <SidebarMenu
        headerTitle="Services"
        menuItems={[{
          name: 'aws',
          label: 'AWS',
          Component: ServiceAWS
        }, {
          name: 'jira',
          label: 'Jira'
        }, {
          name: 'service-now',
          label: 'Service Now'
        }, {
          name: 'pagerduty',
          label: 'Pagerduty'
        }, {
          name: 'git',
          label: 'Git'
        }]}
        onClickItem={setActiveItem}
        activeItem={activeItem}
        onChangeActive={handleItemChange}
      />

      <SidebarMenu
        headerTitle="General"
        menuItems={[{
          name: 'sso',
          label: 'Single Sign-On'
        }, {
          name: 'users',
          label: 'Users and Groups'
        }, {
          name: 'integrations',
          label: 'Integrations'
        }]}
        onClickItem={setActiveItem}
        activeItem={activeItem}
        onChangeActive={handleItemChange}
      />

    </>
  );

};

export default Sidebar;