import React from 'react';
import { Button, Input } from 'semantic-ui-react';
import { Fill, Bar } from '../../../../lib/Misc';

export const CollapsibleTitle = ({ title, helpHandler }) => {

  const handleHelpModal = (handler) => {};

  return (
    <>
      <span>{title}</span>&nbsp;
      {helpHandler && (
        <Button
          size='mini'
          circular
          icon='question'
          basic
          onClick={() => handleHelpModal(helpHandler)}
        />
      )}
    </>
  );
};

export const TableTopBar = ({ onSearch, onClick }) => {
  return (
    <Bar>
      {onSearch && (
        <Input
          size='small'
          label="Search"
          icon='search'
          onChange={onSearch}
        />
      )}
      <Fill />
      <Button
        compact
        color="blue"
        onClick={onClick}>
        New
      </Button>
    </Bar>
  );
};
