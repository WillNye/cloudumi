import React, { useState } from 'react';
import Datatable from '../../../../../../lib/Datatable';
import { DatatableWrapper } from '../../../../../../lib/Datatable/ui/utils';
import { awsOrganizationColumns } from './columns';

const data = [{
  organizationId: 'noq_entrypoint',
  accountId: 3234671289,
  accountName: 'development',
  owner: 'ccastrapel',
  active: true
}];

export const AWSOrganization = () => {

  const [fakeData, setData] = useState([]);

  const handleClick = (action, rowValues) => {};

  const columns = awsOrganizationColumns({ handleClick });
  
  return (
    <DatatableWrapper>
      <Datatable
        data={fakeData}
        columns={columns}
        emptyState={{
          label: 'Create AWS Organization',
          onClick: () => setData(data)
        }}
      />
    </DatatableWrapper>
  );
};
