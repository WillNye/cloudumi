import React from 'react';
import { Section } from 'lib/Section';
import { ScreenHeading } from 'lib/Screen/styles';
import { AWSOrganization } from './components/AWSOrganization';
import { General } from './components/General';
import { HubAccount } from './components/HubAccount';
import { Legacy } from './components/Legacy';
import { SpokeAccounts } from './components/SpokeAccounts';
import { RoleAccessAuth } from './components/RoleAccessAuth';
import { SectionTitle } from '../utils';

export const ServiceAWS = () => {

  return (
    <>

      <ScreenHeading>
        Connect Noq to your AWS accounts
      </ScreenHeading>

      <Section title={<SectionTitle title="Hub Account" helpHandler="hub-account"/>}>
        <HubAccount />
      </Section>

      <Section title={<SectionTitle title="Spoke Accounts" helpHandler="spoke-accounts"/>}>
        <SpokeAccounts />
      </Section>

      <Section title={<SectionTitle title="AWS Organization" helpHandler="aws-organization"/>}>
        <AWSOrganization />
      </Section>

      <Section title={<SectionTitle title="Role Access Authorization" helpHandler="role-access-authorization"/>}>
        <RoleAccessAuth />
      </Section>

      <Section title={<SectionTitle title="General"/>}>
        <General />
      </Section>

      <Section title="Legacy" defaultActive={false} isCollapsible>
        <Legacy />
      </Section>

    </>
  );
};