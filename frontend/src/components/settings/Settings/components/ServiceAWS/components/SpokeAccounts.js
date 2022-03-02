import React, { useEffect } from 'react';
import { useApi } from 'hooks/useApi';
import Datatable from 'lib/Datatable';
import { DatatableWrapper } from 'lib/Datatable/ui/utils';
import { useModal } from 'lib/hooks/useModal';
import { useToast } from 'lib/Toast';
import { NewSpokeAccount } from './forms/NewSpokeAccount';
import { str } from 'components/settings/Settings/strings';

import { spokeAccountsColumns } from './columns';
import { TableTopBar } from '../../utils';

export const SpokeAccounts = () => {

  const { get, post, remove } = useApi('services/aws/account/spoke'); // data/status/empty/error/do
  
  const { error, success } = useToast();

  const { openModal, ModalComponent } = useModal('Add Spoke Account');

  useEffect(() => get.do(), []);

  const handleClick = (action, rowValues) => {
    if (action === 'remove') {
      remove.do({}, `${ rowValues?.name }/${ rowValues?.account_id }`)
      .then(() => {
        success('Hub Account REMOVED');
        get.do();
      })
      .catch(() => error(str.toastErrorMsg));
    }
  };

  const handleClose = post.reset;

  const columns = spokeAccountsColumns({ handleClick });

  const label = `Status: ${get.status}${get.error ? ` / Error: ${get.error}` : ''}`;

  const data = get?.data;

  return (
    <>

      <DatatableWrapper renderAction={data?.length > 0 && <TableTopBar onClick={openModal} />}>
        <Datatable
          data={data}
          columns={columns}
          emptyState={{
            label: 'Connect a Spoke Account',
            onClick: openModal
          }}
          isLoading={get.status === 'working'}
          loadingState={{ label }}
        />
      </DatatableWrapper>

      <ModalComponent onClose={handleClose} hideConfirm>
        <NewSpokeAccount status={post.status} error={post.error} />
      </ModalComponent>

    </>
  );
};
