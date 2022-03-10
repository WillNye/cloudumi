import React, { useState } from 'react'
import { Header, Segment, Icon, Message } from 'semantic-ui-react'
import MonacoDiffComponent from '../blocks/MonacoDiffComponent'
import useEffectivePermissions from './hooks/useEffectivePermissions'

const EffectivePermissions = () => {
  const [error, setError] = useState(null)
  const [messages, setMessages] = useState([])
  const { resourceEffectivePermissions } = useEffectivePermissions()

  const onLintError = (lintErrors) => {
    if (lintErrors.length > 0) {
      setError(true)
      setMessages(JSON.stringify(lintErrors))
    } else {
      setError(false)
      setMessages([])
    }
  }

  // TODO: Make it possible to request a change that removes all unused permissions
  // TODO: Give the user commands to do this manually
  return (
    <>
      <Header as='h2'>
        Effective Permissions
        <Header.Subheader>
          The effective permissions of a role are a combination of the
          permissions contained in a role's inline policies and managed
          policies. The effective permissions are de-duplicated, minimized, and
          alphabetically sorted. The right side shows the effective permissions
          of a role with all permissions removed if they have not been used in
          the last 90 days.
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
          <>
            {error ? (
              <Message warning attached='top'>
                <Icon name='warning' />
                {messages}
              </Message>
            ) : null}

            <MonacoDiffComponent
              onLintError={onLintError}
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
          </>
        ) : null}
      </Segment>
      {/* <JustificationModal handleSubmit={handleAssumeRolePolicySubmit} /> */}
    </>
  )
}

export default EffectivePermissions
