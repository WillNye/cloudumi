import React, { useEffect } from 'react';
import { useApi } from 'hooks/useApi';
import Datatable from 'lib/Datatable';
import { DatatableWrapper } from 'lib/Datatable/ui/utils';
import { useModal } from 'lib/hooks/useModal';
import { useToast } from 'lib/Toast';
import { awsOrganizationColumns } from './columns';
import { NewOrganization } from './forms/NewOrganization';
import { str } from 'components/settings/Settings/strings';

export const AWSOrganization = () => {

  const { get, post, remove } = useApi('services/aws/account/org'); // data/status/empty/error/do
  
  const { error, success } = useToast();

  const { openModal, ModalComponent } = useModal('Add Hub Account');

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
  };

  const handleConfirm = () => {
    post.do().then(() => {
      success('Hub Account CONNECTED');
      get.do();
    });
  };

  const handleClose = post.reset;

  const columns = awsOrganizationColumns({ handleClick });

  const label = `Status: ${get.status}${get.error ? ` / Error: ${get.error}` : ''}`;

  const object = {};

  get.data?.[0]?.forEach((el) => {
    object[el.name] = el.value;
  });

  const data = [object];

  return (
    <>
      <DatatableWrapper>
        <Datatable
          data={data}
          columns={columns}
          emptyState={{
            label: 'Connect an AWS Organization',
            onClick: openModal
          }}
          isLoading={get.status === 'working'}
          loadingState={{ label }}
        />
      </DatatableWrapper>

      <ModalComponent
        onClickToConfirm={handleConfirm}
        onClose={handleClose}>
        <NewOrganization status={post.status} error={post.error} />
      </ModalComponent>

    </>
  );
};
