import React from 'react';
import { CollapsibleSection } from '../../../../../lib/CollapsibleSection';
import { ScreenHeading } from '../../../../../lib/Screen/styles';
import { CollapsibleTitle } from '../utils';
import { Groups } from './components/Groups';
import { Users } from './components/Users';

export const GeneralUsers = () => {

  return (
    <>

      <ScreenHeading>
        Users and Groups
      </ScreenHeading>

      <CollapsibleSection
        title={<CollapsibleTitle title="Users" />}
        defaultActive>
        <Users />
      </CollapsibleSection>

      <CollapsibleSection
        title={<CollapsibleTitle title="Groups" />}
        defaultActive>
        <Groups />
      </CollapsibleSection>

    </>
  );
};