import React, { useContext, useEffect, useState } from 'react';
import { ApiContext } from 'hooks/useApi';

import { Button, Segment } from 'semantic-ui-react';
import { DimmerWithStates } from 'lib/DimmerWithStates';

export const NewOrganization = ({ status = 'working', error, closeModal }) => {

  // waiting/working/done

  const [state, setState] = useState();

  const aws = useContext(ApiContext);

  const isWorking = status === 'working';

  const isSuccess = status === 'done' && !error;

  const hasError = (error && status === 'done');
    
  useEffect(() => {
    let sessionLogs = sessionStorage.getItem('services.aws.logs');
    sessionLogs = sessionLogs ? JSON.parse(sessionLogs) : {};
    if (sessionLogs?.orgAccount?.lastAttempt) {
      setState(sessionLogs?.orgAccount?.lastAttempt);
    }
  }, []);

  const handleClick = () => {
    sessionStorage.setItem('services.aws.logs', JSON.stringify({
      orgAccount: {
        lastAttempt: Date()
      }
    }));
    window.open(aws.data?.central_account_role?.cloudformation_url, '_blank');
    closeModal();
  };

  const isIneligible = aws.data?.central_account_role?.status === 'ineligible';

  return (
    <Segment basic>

      <DimmerWithStates
        loading={isWorking}
        showMessage={hasError}
        messageType={isSuccess ? 'success' : 'warning'}
        message={'Something went wrong, try again!'}
      />

          {/*
            Organization Id: free field string
            Account ID: from spoke account lists
            Account name: from spoke account lists
            Owner: free field string

            add refresh button on our table: like aws
          */}


      {isIneligible ? (
        <p style={{ textAlign: 'center'}}>
          INELIGIBLE! You cannot connect your account, please ask to your admin to help.
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
          <p style={{ textAlign: 'center'}}>
            {!state ? '' : (
              'ATTENTION! You already started this operation, if you closed the tab or something went wrong, try again.'
            )}
          </p>
          <Button
            onClick={handleClick}
            fluid
            positive={!state}
            color={state ? 'blue' : null}>
            {!state ? 'Confirmar' : 'Repeat Operation'}
          </Button>
        </>
      )}

    </Segment>
  )
};
