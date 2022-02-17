import React from 'react';
import { useApi } from '../../../../../../hooks/useApi';
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

  const { get, post } = useApi('api/v3/general/users'); // data/status/empty/error/do

  const { openModal, ModalComponent } = useModal('New User', post.reset, post.reset);

  const handleClick = (action, rowValues) => {
    if (action === 'remove') {
      // Do something
    }
  };

  const columns = userColumns({ handleClick });

  const handleConfirm = () => post.do().then(get.do);

  return (
    <>

      <DatatableWrapper
        renderAction={<TableTopBar onClick={openModal} />}>
        <Datatable
          data={data}
          columns={columns}
          emptyState={{
            label: 'Create User',
            onClick: () => {}
          }}
          isLoading={get.status === 'working' || get.status === 'done'}
          loadingState={{
            label: `TABLE STATUS: ${get.status}${get.error ? ` / Error: ${get.error}` : null}`
          }}
        />
      </DatatableWrapper>

      <ModalComponent
        onClickToConfirm={handleConfirm}>

        Form Fields<br/>
        STATUS: {post.status}{post.error ? ` / Error: ${post.error}` : null}

      </ModalComponent>

    </>
  );
};
