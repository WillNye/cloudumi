import React from 'react';
import Datatable from '../../../../../../lib/Datatable';
import { RowStatusIndicator } from '../../../../../../lib/Misc';
import { DatatableWrapper } from '../../../../../../lib/Datatable/ui/utils';

const data = [{
  accountName: 'noq_entrypoint',
  accountId: 3234671289,
  role: 'NoqCentralRole',
  externalId: '13fdc797-e195-4165-88d0-9982a91b8dfb',
  active: true
}];

export const HubAccount = () => {

  const handleClick = () => {};

  const columns = [{
    Header: 'Account Name',
    accessor: 'accountName'
  }, {
    Header: 'Account ID',
    accessor: 'accountId',
    width: 80
  }, {
    Header: 'Role',
    accessor: 'role',
    width: 80
  }, {
    Header: 'External ID',
    accessor: 'externalId',
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
    <DatatableWrapper>
      <Datatable data={data} columns={columns} />
    </DatatableWrapper>
  );
};
