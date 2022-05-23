import React from 'react'
import TempEscalationAccess from './components/TempEscalationAccess'
// import RoleAccess from './components/RoleAccess'

const ConfigureAccess = ({ elevated_access_config }) => {
  return (
    <>
      {/* RoleAccess work still in progress */}
      {/* <RoleAccess tags={[]} /> */}
      <TempEscalationAccess elevated_access_config={elevated_access_config} />
    </>
  )
}

export default ConfigureAccess
