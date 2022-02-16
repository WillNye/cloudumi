import React from 'react';
import Datatable from '../../../../../../lib/Datatable';
import { DatatableWrapper } from '../../../../../../lib/Datatable/ui/utils';

import { userColumns } from './columns';
import { TableTopBar } from '../../utils';
import { useModal } from '../../../../../../lib/hooks/useModal';

const data = [{
  user: 'curtis',
  enabled: true,
  email: 'curtis@foo.bar',
  updatedAt: '2021-04-04',
  createdAt: '2021-04-01',
  expiration: 'never'
}, {
  user: 'cspilhere',
  enabled: false,
  email: 'cspilhere@foo.bar',
  updatedAt: '2021-04-04',
  createdAt: '2021-04-01',
  expiration: 'never'
}];

export const Users = () => {

  const { openModal, ModalComponent } = useModal('New Group');

  const handleClick = (action, rowValues) => {};

  const columns = userColumns({ handleClick });

  return (
    <>

      <DatatableWrapper
        renderAction={<TableTopBar onClickToAdd={openModal} />}>
        <Datatable
          data={data}
          columns={columns}
          emptyState={{
            label: 'Create User',
            onClick: () => {}
          }}
        />
      </DatatableWrapper>

      <ModalComponent onClickToSave={() => {}}>
        Foo
      </ModalComponent>

    </>
  );
};
