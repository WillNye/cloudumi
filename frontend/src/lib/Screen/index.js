import React from 'react';

import { Container, Content, Sidebar } from './styles';

export const Screen = ({ children, renderSidebar }) => {

  const sidebar = renderSidebar && <Sidebar>{renderSidebar}</Sidebar>;

  return (
    <Container>
      {sidebar}
      <Content>
        {children}
      </Content>
    </Container>
  );
};
