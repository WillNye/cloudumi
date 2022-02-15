import React from 'react';
import { Button, Message, Segment } from 'semantic-ui-react';

export const DatatableWrapper = ({ renderAction, children }) => {

  const renderTopBar = renderAction && (
    <Segment.Group horizontal>
      <Segment textAlign='right'>
        {renderAction}
      </Segment>
    </Segment.Group>
  );

  return (
    <Segment>
      {renderTopBar}
      <Segment>
        {children}
      </Segment>
    </Segment>
  );
};

export const EmptyState = ({ label, onClick }) => {
  return (
    <Segment inverted color='grey' textAlign="center">
      <Button onClick={onClick}>{label}</Button>
    </Segment>
  );
};