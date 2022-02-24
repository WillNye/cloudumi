import React, { useState } from 'react';
import { Button, Checkbox, Message, Segment } from 'semantic-ui-react';
import Datatable from 'lib/Datatable';
import { DatatableWrapper } from 'lib/Datatable/ui/utils';
import { TableTopBar } from '../../utils';
import { roleAccessAuthColumns } from './columns';

const data = [{
  tagName: 'owner-dl',
  allowWebConsole: true,
  authorizations: '549'
}, {
  tagName: 'admin',
  allowWebConsole: false,
  authorizations: '549'
}];

export const RoleAccessAuth = () => {

  const [allowTags, setAllowTags] = useState(false);

  const handleChange = () => {
    setAllowTags(!allowTags);
  };
  const handleClickToAdd = () => {};

  const columns = roleAccessAuthColumns({ disabled: !allowTags });

  const handleHelpModal = (handler) => {};
  
  return (
    <>

      <Message warning>
        <Message.Header>
          <Checkbox
            size="mini"
            toggle
            defaultChecked={allowTags}
            onChange={handleChange}
            label={{ children: 'Enabling the table below you agree with the following rules:' }}
          />
        </Message.Header>
        <Message.List>
          <Message.Item>
            Broker temporary credentials to AWS IAM roles.&nbsp;
            <Button
              size='mini'
              circular
              icon='question'
              basic
              onClick={() => handleHelpModal('aws-iam-roles')}
            />
          </Message.Item>
          <Message.Item>
            Use the following IAM role tag values to identify users and groups authorized to retrieve role credentials.
          </Message.Item>
        </Message.List>
      </Message>

      <Segment basic vertical disabled={!allowTags}>
        <DatatableWrapper renderAction={<TableTopBar disabled={!allowTags} onClick={handleClickToAdd} />}>
          <Datatable data={data} columns={columns} emptyState={{ label: 'Create Tag', onClick: () => {} }} />
        </DatatableWrapper>
      </Segment>

    </>
  );
};
