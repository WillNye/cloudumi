import React, { useState, useEffect } from 'react'
import { Header, Segment } from 'semantic-ui-react'
import MonacoDiffComponent from '../blocks/MonacoDiffComponent'
import { useAuth } from '../../auth/AuthProviderDefault'
import useEffectivePermissions from './hooks/useEffectivePermissions'

const EffectivePermissions = () => {
  // TODO: Put actual account names here
  // const { get } = useApi('services/aws/policies/effective/role/759357822767/development_admin')
  // const { error, success } = useToast()

  // useEffect(() => get.do(), [])

  // const handleRefresh = () => get.do()
  const { sendRequestCommon } = useAuth()
  const [data, setData] = useState('')
  const { resourceEffectivePermissions } = useEffectivePermissions()

  // useEffect(() => {
  //   async function fetchData() {
  //     const resJson = await sendRequestCommon(
  //       null,
  //       '/api/v3/services/aws/policies/effective/role/759357822767/development_admin',
  //       'get'
  //     )
  //     if (!resJson) {
  //       return
  //     }
  //     setData(resJson.data)
  //   }
  //   fetchData()
  // }, [sendRequestCommon])

  return (
    <>
      <Header as='h2'>
        Effective Permissions
        <Header.Subheader>
          The effective permissions of a role is a combination of the
          permissions contained in a role's inline policies and managed
          policies. The effective permissions are de-duplicated, minimized, and
          alphabetically sorted. This is shown side-by-side with the role's
          effective policy with all unused permissions removed.
        </Header.Subheader>
      </Header>
      <Segment
        attached
        style={{
          border: 0,
          padding: 0,
        }}
      >
        {resourceEffectivePermissions ? (
          <MonacoDiffComponent
            oldValue={JSON.stringify(
              resourceEffectivePermissions.effective_policy,
              null,
              2
            )}
            newValue={JSON.stringify(
              resourceEffectivePermissions.effective_policy_unused_permissions_removed,
              null,
              2
            )}
            // readOnly={
            //   (!config.can_update_cancel && !config.can_approve_reject) ||
            //   changeReadOnly
            // }
            //  onLintError={onLintError}
            //  onValueChange={onValueChange}
          />
        ) : null}
      </Segment>
      {/* <JustificationModal handleSubmit={handleAssumeRolePolicySubmit} /> */}
    </>
  )
}

export default EffectivePermissions
