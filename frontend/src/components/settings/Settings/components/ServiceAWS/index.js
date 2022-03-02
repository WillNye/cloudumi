import React from 'react';
import { Section } from 'lib/Section';
import { AWSOrganization } from './components/AWSOrganization';
import { General } from './components/General';
import { HubAccount } from './components/HubAccount';
import { Legacy } from './components/Legacy';
import { SpokeAccounts } from './components/SpokeAccounts';
import { RoleAccessAuth } from './components/RoleAccessAuth';
import { SectionTitle } from '../utils';
import { ApiGetProvider } from 'hooks/useApi';

export const ServiceAWS = () => {
  return (
    <ApiGetProvider pathname="integrations/aws">

      <Section
        title={<SectionTitle title='Hub Account' helpHandler='hub-account' />}
      >
        <HubAccount />
      </Section>

      <Section
        title={
          <SectionTitle title='Spoke Accounts' helpHandler='spoke-accounts' />
        }
      >
        <SpokeAccounts />
      </Section>

      <Section
        title={
          <SectionTitle
            title='AWS Organization'
            helpHandler='aws-organization'
          />
        }
      >
        <AWSOrganization />
      </Section>

      <Section
        title={
          <SectionTitle
            title='Role Access Authorization'
            helpHandler='role-access-authorization'
          />
        }
      >
        <RoleAccessAuth />
      </Section>

      <Section title={<SectionTitle title='General' />}>
        <General />
      </Section>

      <Section title='Legacy' defaultActive={false} isCollapsible>
        <Legacy />
      </Section>

    </ApiGetProvider>
  );
};
