import React from 'react'
import { Section } from 'lib/Section'
import { AWSOrganization } from './components/AWSOrganization'
import { General } from './components/General'
import { HubAccount } from './components/HubAccount'
import { SpokeAccounts } from './components/SpokeAccounts'
import RoleAuthorization from './components/RoleAuthorization'
import { SectionTitle } from '../utils'
import { ApiGetProvider } from 'hooks/useApi'

export const ServiceAWS = () => {
  return (
    <ApiGetProvider pathname='integrations/aws'>
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

      <RoleAuthorization />

      <Section title={<SectionTitle title='General' />}>
        <General />
      </Section>
    </ApiGetProvider>
  )
}
