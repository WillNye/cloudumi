import React from 'react'
import TempEscalationAccess from './components/TempEscalationAccess'
import RoleAccess from './components/RoleAccess'

const ConfigureAccess = ({ elevated_access_config, role_access_config }) => {
  return (
    <>
      {role_access_config && (
        <RoleAccess role_access_config={role_access_config} />
      )}
      {elevated_access_config && (
        <TempEscalationAccess elevated_access_config={elevated_access_config} />
      )}
    </>
  )
}

export default ConfigureAccess
