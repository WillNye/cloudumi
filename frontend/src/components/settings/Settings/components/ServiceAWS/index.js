import React from 'react';
import { CollapsibleSection } from '../../../../../lib/CollapsibleSection';
import { ScreenHeading } from '../../../../../lib/Screen/styles';
import { AWSOrganization } from './components/AWSOrganization';
import { General } from './components/General';
import { HubAccount } from './components/HubAccount';
import { Legacy } from './components/Legacy';
import { SpokeAccounts } from './components/SpokeAccounts';

import { Button } from 'semantic-ui-react';

export const ServiceAWS = () => {

  const generateTitle = (title, helpHandler) => {

    const handleHelpModal = (handler) => {};

    return (
      <>
        <span>{title}</span>&nbsp;
        <Button
          size='mini'
          circular
          icon='question'
          basic
          onClick={() => handleHelpModal(helpHandler)}
        />
      </>
    );
  };

  return (
    <>

      <ScreenHeading>
        Connect Noq to your AWS accounts
      </ScreenHeading>

      <CollapsibleSection
        title={generateTitle('Hub Account', 'hub-account')}
        defaultActive={true}>
        <HubAccount />
      </CollapsibleSection>

      <CollapsibleSection
        title={generateTitle('Spoke Accounts', 'spoke-accounts')}
        defaultActive={true}>
        <SpokeAccounts />
      </CollapsibleSection>

      <CollapsibleSection
        title={generateTitle('AWS Organization', 'aws-organization')}
        defaultActive={true}>
        <AWSOrganization />
      </CollapsibleSection>

      <CollapsibleSection
        title={generateTitle('General', 'general')}
        defaultActive={true}>
        <General />
      </CollapsibleSection>

      <CollapsibleSection title="Legacy">
        <Legacy />
      </CollapsibleSection>

    </>
  );
};