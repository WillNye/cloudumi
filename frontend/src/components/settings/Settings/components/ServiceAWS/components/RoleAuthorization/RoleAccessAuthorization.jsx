import React from 'react'
import { Section } from 'lib/Section'
import { RoleAccessAuth } from './components/RoleAccessAuth'
import { EnablingTraAccessAuth } from './components/EnablingTraAccessAuth'
import { SectionTitle } from '../../../utils'

export const RoleAccessAuthorization = () => {
  return (
    <>
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

      <Section
        title={
          <SectionTitle
            title='Temporary Role Access'
            helpHandler='temporary-role-access'
          />
        }
      >
        <EnablingTraAccessAuth />
      </Section>
    </>
  )
}

export default RoleAccessAuthorization;
