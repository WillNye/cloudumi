import React from 'react';
import { CollapsibleSection } from '../../../../../lib/CollapsibleSection';
import { ScreenHeading } from '../../../../../lib/Screen/styles';
import { AWSOrganization } from './components/AWSOrganization';
import { General } from './components/General';
import { HubAccount } from './components/HubAccount';
import { Legacy } from './components/Legacy';
import { SpokeAccounts } from './components/SpokeAccounts';
import { RoleAccessAuth } from './components/RoleAccessAuth';
import { CollapsibleTitle } from '../utils';

export const ServiceAWS = () => {

  return (
    <>

      <ScreenHeading>
        Connect Noq to your AWS accounts
      </ScreenHeading>

      <CollapsibleSection
        title={<CollapsibleTitle title="Hub Account" helpHandler="hub-account"/>}
        defaultActive>
        <HubAccount />
      </CollapsibleSection>

      <CollapsibleSection
        title={<CollapsibleTitle title="Spoke Accounts" helpHandler="spoke-accounts"/>}
        defaultActive>
        <SpokeAccounts />
      </CollapsibleSection>

      <CollapsibleSection
        title={<CollapsibleTitle title="AWS Organization" helpHandler="aws-organization"/>}
        defaultActive>
        <AWSOrganization />
      </CollapsibleSection>

      <CollapsibleSection
        title={<CollapsibleTitle title="Role Access Authorization" helpHandler="role-access-authorization"/>}
        defaultActive>
        <RoleAccessAuth />
      </CollapsibleSection>

      <CollapsibleSection
        title={<CollapsibleTitle title="General"/>}
        defaultActive>
        <General />
      </CollapsibleSection>

      <CollapsibleSection title="Legacy">
        <Legacy />
      </CollapsibleSection>

    </>
  );
};