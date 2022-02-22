import React from 'react';
import { Button, Checkbox } from 'semantic-ui-react';

export const General = () => {
  
  const handleHelpModal = (handler) => {};
  
  return (
    <>
      <Checkbox
        label={{ children: (
          <>
            Automatically update role trust policies when an authorized user requests credentials,
            but Noq isn't authorized to perform the role assumption.
          </>
        )}}
      />
      &nbsp;
      <Button
        size='mini'
        circular
        icon='question'
        basic
        onClick={() => handleHelpModal('noq-auth')}
      />
    </>
  );
};
