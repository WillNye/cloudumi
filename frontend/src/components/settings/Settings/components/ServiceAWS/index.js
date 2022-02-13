import React from 'react';
import { CollapsibleSection } from '../../../../../lib/CollapsibleSection';
import { ScreenHeading } from '../../../../../lib/Screen/styles';
import { AWSOrganization } from './components/AWSOrganization';
import { General } from './components/General';
import { HubAccount } from './components/HubAccount';
import { Legacy } from './components/Legacy';
import { SpokeAccounts } from './components/SpokeAccounts';

export const ServiceAWS = () => {

  return (
    <>

      <ScreenHeading>
        Connect Noq to your AWS accounts
      </ScreenHeading>

      <CollapsibleSection title="Hub Account" defaultActive={true}>
        <HubAccount />
      </CollapsibleSection>

      <CollapsibleSection title="Spoke Accounts" defaultActive={true}>
        <SpokeAccounts />
      </CollapsibleSection>

      <CollapsibleSection title="AWS Organization" defaultActive={true}>
        <AWSOrganization />
      </CollapsibleSection>

      <CollapsibleSection title="General" defaultActive={true}>
        <General />
      </CollapsibleSection>

      <CollapsibleSection title="Legacy">
        <Legacy />
      </CollapsibleSection>

    </>
  );
};