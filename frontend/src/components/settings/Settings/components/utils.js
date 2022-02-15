import React from 'react';
import { Button } from 'semantic-ui-react';

export const generateTitle = (title, helpHandler) => {

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
