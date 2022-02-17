import React from 'react';
import { useApi } from '../../../../../../hooks/useApi';
import Datatable from '../../../../../../lib/Datatable';
import { DatatableWrapper } from '../../../../../../lib/Datatable/ui/utils';
import { useModal } from '../../../../../../lib/hooks/useModal';
import { hubAccountColumns } from './columns';

const data = [{
  accountName: 'noq_entrypoint',
  accountId: 3234671289,
  role: 'NoqCentralRole',
  externalId: '13fdc797-e195-4165-88d0-9982a91b8dfb',
  active: true
}];

export const HubAccount = () => {

  const { get, post, remove } = useApi('api/v3/services/aws/account/hub'); // data/status/empty/error/do

  const { openModal, ModalComponent } = useModal('Add Hub Account', post.reset, post.reset);

  const handleClick = (action, rowValues) => {
    if (action === 'remove') {
      remove.do(rowValues.id); // Assuming should we gonna use an Id to delete
    }
  };

  const columns = hubAccountColumns({ handleClick });

  const handleConfirm = () => post.do().then(get.do);

  return (
    <>

      <DatatableWrapper>
        <Datatable
          data={get.data || data}
          columns={columns}
          emptyState={{
            label: 'Create Hub Account',
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
