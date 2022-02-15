import React from 'react';
import { CollapsibleSection } from '../../../../../lib/CollapsibleSection';
import { ScreenHeading } from '../../../../../lib/Screen/styles';
import { AWSOrganization } from './components/AWSOrganization';
import { General } from './components/General';
import { HubAccount } from './components/HubAccount';
import { Legacy } from './components/Legacy';
import { SpokeAccounts } from './components/SpokeAccounts';
import { RoleAccessAuth } from './components/RoleAccessAuth';
import { generateTitle } from '../utils';

export const ServiceAWS = () => {

  return (
    <>

      <ScreenHeading>
        Connect Noq to your AWS accounts
      </ScreenHeading>

      <CollapsibleSection
        title={generateTitle('Hub Account', 'hub-account')}
        defaultActive>
        <HubAccount />
      </CollapsibleSection>

      <CollapsibleSection
        title={generateTitle('Spoke Accounts', 'spoke-accounts')}
        defaultActive>
        <SpokeAccounts />
      </CollapsibleSection>

      <CollapsibleSection
        title={generateTitle('AWS Organization', 'aws-organization')}
        defaultActive>
        <AWSOrganization />
      </CollapsibleSection>

      <CollapsibleSection
        title={generateTitle('Role Access Authorization', 'role-access-authorization')}
        defaultActive>
        <RoleAccessAuth />
      </CollapsibleSection>

      <CollapsibleSection
        title={generateTitle('General')}
        defaultActive>
        <General />
      </CollapsibleSection>

      <CollapsibleSection title="Legacy">
        <Legacy />
      </CollapsibleSection>

    </>
  );
};