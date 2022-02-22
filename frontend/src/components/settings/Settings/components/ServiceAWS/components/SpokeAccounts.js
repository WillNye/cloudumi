import React from 'react';
import { useApi } from '../../../../../../hooks/useApi';
import Datatable from '../../../../../../lib/Datatable';
import { DatatableWrapper } from '../../../../../../lib/Datatable/ui/utils';
import { spokeAccountsColumns } from './columns';
import { useModal } from '../../../../../../lib/hooks/useModal';
import { TableTopBar } from '../../utils';

// const data = [{
//   accountName: 'noq_entrypoint',
//   accountId: 3234671289,
//   role: 'NoqCentralRole',
//   accountAdmin: 'team_a@noq.com',
//   active: true
// }, {
//   accountName: 'noq_entrypoint',
//   accountId: 3234671289,
//   role: 'NoqCentralRole',
//   accountAdmin: 'team_a@noq.com',
//   active: false
// }];

export const SpokeAccounts = () => {

  const { get, post } = useApi('api/v3/services/aws/account/spoke'); // data/status/empty/error/do

  const { openModal, ModalComponent } = useModal('Add Spoke Account', post.reset, post.reset);

  const handleClick = (action, rowValues) => {
    if (action === 'remove') {
      // Do something
    }
  };

  const columns = spokeAccountsColumns({ handleClick });

  const handleConfirm = () => post.do().then(get.do);

  return (
    <>

      <DatatableWrapper renderAction={<TableTopBar onClick={openModal} />}>
        <Datatable
          data={get.data}
          columns={columns}
          emptyState={{
            label: 'Connect a Spoke Account',
            onClick: openModal
          }}
          isLoading={get.status === 'working' || get.status === 'done'}
          loadingState={{
            label: `TABLE STATUS: ${get.status}${get.error ? ` / Error: ${get.error}` : null}`
          }}
        />
      </DatatableWrapper>

      <ModalComponent
        onClickToConfirm={handleConfirm}>

        Image/Diagram/Etc<br/>
        STATUS: {post.status}{post.error ? ` / Error: ${post.error}` : null}

      </ModalComponent>

    </>
  );
};
