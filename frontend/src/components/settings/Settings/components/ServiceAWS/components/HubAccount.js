import React, { useEffect } from 'react';
import { useApi } from 'hooks/useApi';
import Datatable from 'lib/Datatable';
import { DatatableWrapper } from 'lib/Datatable/ui/utils';
import { useModal } from 'lib/hooks/useModal';
import { useToast } from 'lib/Toast';
import { hubAccountColumns } from './columns';
import { NewHubAccount } from './forms/NewHubAccount';
import { str } from 'components/settings/Settings/strings';

export const HubAccount = () => {

  const { get, post, remove } = useApi('services/aws/account/hub'); // data/status/empty/error/do
  
  const { error, success } = useToast();

  const { openModal, ModalComponent } = useModal('Add Hub Account');

  useEffect(() => {
    get.do();
  }, []);

  const handleClick = (action, rowValues) => {
    if (action === 'remove') {
      remove.do(rowValues.id) // Assuming should we gonna use an Id to delete
      .then(() => {
        success('Hub Account REMOVED');
        get.do();
      })
      .catch(() => error(str.toastErrorMsg));
    }
  };

  const handleConfirm = () => {
    post.do().then(() => {
      success('Hub Account CONNECTED');
      get.do();
    });
  };

  const handleClose = () => {
    post.reset();
  };

  const columns = hubAccountColumns({ handleClick });

  const label = `Status: ${get.status}${get.error ? ` / Error: ${get.error}` : ''}`;

  return (
    <>

      <DatatableWrapper>
        <Datatable
          data={get.data}
          columns={columns}
          emptyState={{
            label: 'Connect Hub Account',
            onClick: openModal
          }}
          isLoading={get.status === 'working' || get.status === 'done'}
          loadingState={{ label }}
        />
      </DatatableWrapper>

      <ModalComponent
        onClickToConfirm={handleConfirm}
        onClose={handleClose}>
        <NewHubAccount status={post.status} error={post.error} />
      </ModalComponent>

    </>
  );
};
