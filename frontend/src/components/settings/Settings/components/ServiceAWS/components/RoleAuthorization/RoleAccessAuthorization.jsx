import React, { useState } from 'react'
import { Section } from 'lib/Section'
import { RoleAccessAuth } from './components/RoleAccessAuth'
import { EnablingTraAccessAuth } from './components/EnablingTraAccessAuth'
import { SectionTitle } from '../../../utils'

export const RoleAccessAuthorization = () => {
  const [accessData, setAccessData] = useState({
    tra_access: false,
    role_access: false,
  })

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
        <RoleAccessAuth setAccessData={setAccessData} accessData={accessData} />
      </Section>

      <Section
        title={
          <SectionTitle
            title='Temporary Role Access'
            helpHandler='temporary-role-access'
          />
        }
      >
        <EnablingTraAccessAuth
          setAccessData={setAccessData}
          accessData={accessData}
        />
      </Section>
    </>
  )
}

export default RoleAccessAuthorization
