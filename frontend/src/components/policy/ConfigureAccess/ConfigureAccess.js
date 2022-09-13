import React from 'react'
import TempEscalationAccess from './components/TempEscalationAccess'
import RoleAccess from './components/RoleAccess'
import { Divider, Header } from 'semantic-ui-react'
import { Link } from 'react-router-dom'

const ConfigureAccess = ({ elevated_access_config, role_access_config }) => {
  return (
    <>
      <Header as='h3'>Role Access</Header>
      {role_access_config ? (
        <RoleAccess role_access_config={role_access_config} />
      ) : (
        <p>
          Contact Admin to setup and enable Role Access. This can be globally
          configured on the&nbsp;
          <Link to='/settings'>settings</Link> page.
        </p>
      )}
      <Divider horizontal />
      <>
        <Header as='h3'>Temporary Escalation Access</Header>
        {elevated_access_config ? (
          <TempEscalationAccess
            elevated_access_config={elevated_access_config}
          />
        ) : (
          <p>
            Contact Admin to setup and enable Temporary Escalation Access. This
            can be globally configured on the&nbsp;
            <Link to='/settings'>settings</Link> page.
          </p>
        )}
      </>
    </>
  )
}

export default ConfigureAccess
