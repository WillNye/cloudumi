import React from 'react';
import Datatable from '../../../../../../lib/Datatable';
import { Checkbox } from 'semantic-ui-react';
import { DatatableWrapper } from '../../../../../../lib/Datatable/ui/utils';

const data = [{
  tagName: 'owner-dl',
  allowWebConsole: true,
  authorizations: '549'
}, {
  tagName: 'admin',
  allowWebConsole: false,
  authorizations: '549'
}];

export const General = () => {

  const handleChange = () => {};
  const handleClickToAdd = () => {};

  const columns = [{
    Header: 'Tag Name',
    accessor: 'tagName'
  }, {
    Header: 'Authorizations',
    accessor: 'authorizations',
    width: 60,
    align: 'center'
  }, {
    Header: 'Allow Web Console Access',
    accessor: 'allowWebConsole',
    align: 'right',
    Cell: ({ row }) => (
      <Checkbox toggle onChange={handleChange} checked={row?.values?.allowWebConsole} />
    )
  }];
  
  return (
    <DatatableWrapper renderAction={<button onClick={handleClickToAdd}>Add</button>}>
      <Datatable data={data} columns={columns} />
    </DatatableWrapper>
  );
};
