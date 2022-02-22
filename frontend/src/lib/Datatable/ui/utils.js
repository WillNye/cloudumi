import React from 'react';
import { Button, Segment } from 'semantic-ui-react';
import styled from 'styled-components';
import { Bar } from '../../Misc';

const CustomBar = styled(Bar)`
  margin: 25px 0 0;
  display: block;
`

export const DatatableWrapper = ({ renderAction, children }) => {

  const renderTopBar = renderAction && (
    <Bar>
      {renderAction}
    </Bar>
  );

  return (
    <Segment>
      {renderTopBar}
      <CustomBar basic>
        {children}
      </CustomBar>
    </Segment>
  );
};

export const EmptyState = ({ label, onClick }) => {
  return (
    <Segment basic inverted color='grey' textAlign="center">
      <Button onClick={onClick}>{label}</Button>
    </Segment>
  );
};

export const LoadingState = ({ label }) => {
  return (
    <Segment basic inverted color='grey' textAlign="center">
      <Button disabled>{label}</Button>
    </Segment>
  );
};