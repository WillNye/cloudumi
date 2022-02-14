import React from 'react';
import Datatable from '../../../../../../lib/Datatable';
import { RowStatusIndicator } from '../../../../../../lib/Misc';
import { DatatableWrapper } from '../../../../../../lib/Datatable/ui/utils';

const data = [{
  organizationId: 'noq_entrypoint',
  accountId: 3234671289,
  accountName: 'development',
  owner: 'ccastrapel',
  active: true
}];

export const AWSOrganization = () => {

  const handleClick = () => {};

  const columns = [{
    Header: 'Organization ID',
    accessor: 'organizationId',
  }, {
    Header: 'Account ID',
    accessor: 'accountId',
  }, {
    Header: 'Account Name',
    accessor: 'accountName',
  }, {
    Header: 'Owner',
    accessor: 'owner',
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
