import React from 'react';

import { Segment } from 'semantic-ui-react';
import { DimmerWithStates } from 'lib/DimmerWithStates';

export const NewHubAccount = ({ status = 'working', error }) => {

  // waiting/working/done

  const isWorking = status === 'working';

  const isSuccess = status === 'done' && !error;

  const hasError = (error && status === 'done');
  
  return (
    <Segment basic>

      <DimmerWithStates
        loading={isWorking}
        showMessage={hasError}
        messageType={isSuccess ? 'success' : 'warning'}
        message={'Something went wrong, try again!'}
      />

      <p style={{ textAlign: 'center'}}>
        <br /><br /><br />
        How we gonna connect your Hub Account?
        <br /><br /><br />
      </p>

    </Segment>
  )
};
