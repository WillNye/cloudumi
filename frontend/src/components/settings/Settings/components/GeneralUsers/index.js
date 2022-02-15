import React from 'react';
import { CollapsibleSection } from '../../../../../lib/CollapsibleSection';
import { ScreenHeading } from '../../../../../lib/Screen/styles';
import { generateTitle } from '../utils';

export const GeneralUsers = () => {

  return (
    <>

      <ScreenHeading>
        Users and Groups
      </ScreenHeading>

      <CollapsibleSection
        title={generateTitle('Users')}
        defaultActive>
        Users
      </CollapsibleSection>

      <CollapsibleSection
        title={generateTitle('Groups')}
        defaultActive>
        Groups
      </CollapsibleSection>

    </>
  );
};