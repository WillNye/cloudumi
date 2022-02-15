import React from 'react';
import Datatable from '../../../../../../lib/Datatable';
import { DatatableWrapper } from '../../../../../../lib/Datatable/ui/utils';
import { hubAccountColumns } from './columns';

const data = [{
  accountName: 'noq_entrypoint',
  accountId: 3234671289,
  role: 'NoqCentralRole',
  externalId: '13fdc797-e195-4165-88d0-9982a91b8dfb',
  active: true
}];

export const HubAccount = () => {

  const handleClick = (action, rowValues) => {};

  const columns = hubAccountColumns({ handleClick });
  
  return (
    <DatatableWrapper>
      <Datatable data={data} columns={columns} emptyState={{ label: 'Create Hub Account', onClick: () => {} }} />
    </DatatableWrapper>
  );
};
