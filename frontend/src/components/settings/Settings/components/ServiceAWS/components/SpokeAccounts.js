import React, { useState } from 'react';
import Datatable from '../../../../../../lib/Datatable';
import { RowStatusIndicator } from '../../../../../../lib/Misc';
import { DatatableWrapper } from '../../../../../../lib/Datatable/ui/utils';

import { Button, Modal } from 'semantic-ui-react';

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

  const handleClick = () => {};
  const handleClickToAdd = () => {
    setModal(true);
  };
  
  const columns = [{
    Header: 'Account Name',
    accessor: 'accountName'
  }, {
    Header: 'Account ID',
    accessor: 'accountId'
  }, {
    Header: 'Role',
    accessor: 'role'
  }, {
    Header: 'Account Admin',
    accessor: 'accountAdmin'
  }, {
    Header: 'Status',
    accessor: 'active',
    width: 60,
    align: 'center',
    Cell: ({ row }) => (
      <RowStatusIndicator isActive={row?.values?.active} />
    )
  }, {
    Header: 'Actions',
    width: 80,
    align: 'right',
    Cell: ({ row }) => (
      <button onClick={() => handleClick(row?.values)}>
        Remove
      </button>
    )
  }];
  
  return (
    <>

      <DatatableWrapper renderAction={<button onClick={handleClickToAdd}>Add</button>}>
        <Datatable data={data} columns={columns} />
      </DatatableWrapper>

      <Modal header='New Spoke Account' open={modalIsOpen}>
        <Modal.Content>
          Spoke Account Form
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
