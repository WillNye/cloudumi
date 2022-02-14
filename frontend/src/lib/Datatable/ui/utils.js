import React from 'react';
import { Segment } from 'semantic-ui-react';

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
