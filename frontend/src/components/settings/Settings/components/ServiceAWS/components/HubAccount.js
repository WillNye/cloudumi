/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect } from 'react';
import { useApi } from 'hooks/useApi';
import Datatable from 'lib/Datatable';
import { DatatableWrapper, RefreshButton } from 'lib/Datatable/ui/utils';
import { useModal } from 'lib/hooks/useModal';
import { useToast } from 'lib/Toast';
import { hubAccountColumns } from './columns';
import { NewHubAccount } from './forms/NewHubAccount';
import { str } from 'components/settings/Settings/strings';
import { TableTopBar } from '../../utils';

export const HubAccount = () => {

  const { get, post, remove } = useApi('services/aws/account/hub')

  const { error, success } = useToast()

  const { openModal, closeModal, ModalComponent } = useModal('Add Hub Account');

  useEffect(() => get.do(), []);

  const handleClick = (action, rowValues) => {
    if (action === 'remove') {
      remove.do({ account_id: rowValues?.account_id })
      .then(() => {
        success('Hub Account REMOVED');
        get.do();
      })
      .catch(() => error(str.toastErrorMsg));
    }
  }

  const handleClose = post.reset;

  const columns = hubAccountColumns({ handleClick })

  const label = `Status: ${get.status}${
    get.error ? ` / Error: ${get.error}` : ''
  }`

  let data = get.data;

  // TODO: Remove after fixed in the API
  if (!Array.isArray(data) && get.status === 'done' && !get.empty && Object.keys(data)?.length > 0) {
    data = [data];
  } else {
    data = null;
  }

  const isWorking = get.status === 'working';

  const handleRefresh = () => get.do();

  return (
    <>

      <DatatableWrapper
        isLoading={remove.status === 'working'}
        renderAction={(
          <TableTopBar
            extras={<RefreshButton disabled={isWorking} onClick={handleRefresh}/>}
          />
        )}>
        <Datatable
          data={data}
          columns={columns}
          emptyState={{
            label: 'Connect Hub Account',
            onClick: openModal,
          }}
          isLoading={isWorking}
          loadingState={{ label }}
        />
      </DatatableWrapper>

      <ModalComponent onClose={handleClose} hideConfirm>
        <NewHubAccount closeModal={closeModal} />
      </ModalComponent>

    </>
  )
}
