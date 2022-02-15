import React, { useState } from 'react';
import Datatable from '../../../../../../lib/Datatable';
import { DatatableWrapper } from '../../../../../../lib/Datatable/ui/utils';

import { Button, Modal } from 'semantic-ui-react';
import { spokeAccountsColumns } from './columns';
import { NewSpokeAccountForm } from './NewSpokeAccountForm';

const data = [{
  accountName: 'noq_entrypoint',
  accountId: 3234671289,
  role: 'NoqCentralRole',
  accountAdmin: 'team_a@noq.com',
  active: true
}, {
  accountName: 'noq_entrypoint',
  accountId: 3234671289,
  role: 'NoqCentralRole',
  accountAdmin: 'team_a@noq.com',
  active: false
}];

export const SpokeAccounts = () => {

  const [modalIsOpen, setModal] = useState(false);

  const handleClick = (action, rowValues) => {};

  const handleClickToAdd = () => {
    setModal(true);
  };

  const columns = spokeAccountsColumns({ handleClick });

  return (
    <>

      <DatatableWrapper
        renderAction={(
          <Button
            compact
            color="blue"
            onClick={handleClickToAdd}>
            Add
          </Button>        
        )}>
        <Datatable data={data} columns={columns} emptyState={{ label: 'Create Spoke Account', onClick: () => {} }} />
      </DatatableWrapper>

      <Modal open={modalIsOpen}>
        <Modal.Header>
          New Spoke Account
        </Modal.Header>
        <Modal.Content>
          <NewSpokeAccountForm />
        </Modal.Content>
        <Modal.Actions>
          <Button onClick={() => setModal(!modalIsOpen)}>
            Cancel
          </Button>
          <Button onClick={() => setModal(!modalIsOpen)} positive>
            Save
          </Button>
        </Modal.Actions>          
      </Modal>

    </>
  );
};
