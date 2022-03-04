import React, { useContext } from 'react';
import { ApiContext } from 'hooks/useApi';

import { Button, Segment } from 'semantic-ui-react';

export const NewSpokeAccount = ({ closeModal }) => {

  const aws = useContext(ApiContext);
    
  const handleClick = () => {
    window.open(aws.data?.spoke_account_role?.cloudformation_url, '_blank');
    closeModal();
  };

  const isIneligible = aws.data?.spoke_account_role?.status === 'ineligible';
  
  return (
    <Segment basic>

      {isIneligible ? (
        <p style={{ textAlign: 'center'}}>
          You cannot connect your Spoke Accounts before having a Hub Account connected.
        </p>
      ) : (
        <>
          <p style={{ textAlign: 'center'}}>
            <br /><br /><br />
            Hello human, we gonna open a new tab to connect your account. Please follow the instructions below:<br />
            - A new tab will be opened to complete the process;<br />
            - Once you have the process completed, just close the tab;<br />
            - After you click to confirm please wait a couple of minutes to check if everything works;<br />
            <br /><br /><br />
          </p>
          <Button onClick={handleClick} fluid positive>Confirm</Button>
        </>
      )}

    </Segment>
  )
};
