import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Header,
  Segment,
  Icon,
  Message,
  Tab,
  Button,
  Divider,
  Grid,
} from 'semantic-ui-react'
import MonacoDiffComponent from '../blocks/MonacoDiffComponent'
import useEffectivePermissions from './hooks/useEffectivePermissions'
import { JustificationModal } from './PolicyModals'
import { BasePolicyMonacoEditor } from './PolicyMonacoEditor'

const EffectivePermissions = () => {
  const [error, setError] = useState(null)
  const [messages, setMessages] = useState([])

  // Existing value which is the modified Unused Policy value. This only applies on the
  // Simplified Policy excluding Unused Permissions pane
  const [value, setValue] = useState(null)

  // The value of the Simplified Policy, only applies to the pane that only views the Simplifed Permissions
  // and not the Simplifed Permissions that exclude unused permissions.
  const [simplifiedPolicyValue, setSimplifedPolicyValue] = useState(null)
  const [activePaneText, setActivePaneText] = useState('Simplified Policy')

  const setActivePane = (e, data) => {
    const menuItem = data.panes[data.activeIndex]
    setActivePaneText(menuItem.menuItem)
  }

  const {
    resourceEffectivePermissions,
    handleEffectivePolicySubmit,
    setModalWithAdminAutoApprove,
    setNewStatement,
    setRemoveUnusedPermissions,
  } = useEffectivePermissions()

  const unUsedPermissions = useMemo(() => {
    return (
      resourceEffectivePermissions?.effective_policy_unused_permissions_removed ||
      null
    )
  }, [resourceEffectivePermissions])

  useEffect(
    function onUnUsedPermissionsUpdate() {
      if (unUsedPermissions) {
        setNewStatement(unUsedPermissions)
        setValue(JSON.stringify(unUsedPermissions, null, 2))
      }
    },
    [unUsedPermissions, setNewStatement]
  )

  const onLintError = (lintErrors) => {
    if (lintErrors.length > 0) {
      setError(true)
      setMessages(JSON.stringify(lintErrors))
    } else {
      setError(false)
      setMessages([])
    }
  }

  const onValueChange = (newValue) => {
    setValue(newValue)
  }

  const onEffectivePolicySubmit = useCallback(() => {
    setNewStatement(JSON.parse(value))
    setRemoveUnusedPermissions(true)
    setModalWithAdminAutoApprove(false)
  }, [
    value,
    setNewStatement,
    setModalWithAdminAutoApprove,
    setRemoveUnusedPermissions,
  ])

  const onSimplifedPolicySubmit = useCallback(() => {
    setNewStatement(
      JSON.parse(simplifiedPolicyValue) ||
        resourceEffectivePermissions?.effective_policy
    )
    setRemoveUnusedPermissions(false)
    setModalWithAdminAutoApprove(false)
  }, [
    simplifiedPolicyValue,
    setNewStatement,
    resourceEffectivePermissions,
    setModalWithAdminAutoApprove,
    setRemoveUnusedPermissions,
  ])

  const onSimplifedPolicyChange = (newValue) => {
    setSimplifedPolicyValue(newValue)
  }

  const panes = [
    {
      menuItem: 'Simplified Policy',
      render: () => (
        <Tab.Pane attached={false}>
          <>
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

                  <BasePolicyMonacoEditor
                    policy={resourceEffectivePermissions.effective_policy}
                    readOnly={false}
                    onChange={onSimplifedPolicyChange}
                  />
                </>
              ) : null}
            </Segment>
          </>
        </Tab.Pane>
      ),
    },
    {
      menuItem: 'Simplified Policy, excluding Unused Permissions',
      render: () => (
        <Tab.Pane attached={false}>
          <>
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
                  {resourceEffectivePermissions.effective_policy !==
                  resourceEffectivePermissions.effective_policy_unused_permissions_removed ? (
                    <MonacoDiffComponent
                      renderSideBySide={true}
                      onLintError={onLintError}
                      onValueChange={onValueChange}
                      oldValue={JSON.stringify(
                        resourceEffectivePermissions.effective_policy,
                        null,
                        2
                      )}
                      newValue={JSON.stringify(unUsedPermissions, null, 2)}
                      enableJSON={true}
                      enableTerraform={false}
                      enableCloudFormation={false}
                      readOnly={false}
                    />
                  ) : (
                    <BasePolicyMonacoEditor
                      onLintError={onLintError}
                      policy={resourceEffectivePermissions.effective_policy}
                    />
                  )}
                </>
              ) : null}
            </Segment>
          </>
        </Tab.Pane>
      ),
    },
  ]

  // TODO: Give the user commands to do this manually
  return (
    <>
      <Header as='h2'>
        Simplified Policy
        <Header.Subheader>
          <br />
          This feature shows a simplified version of your identity's
          permissions. A policy is simplified by combining all of the identity's
          inline and managed policies into a single policy. Permissions are then
          de-duplicated and alphabetically sorted. This view also utilizes data
          from Access Advisor to show permissions that have not been used in the
          last 90 days. Please read the
          <a href='/docs/features/permissions_management_and_request_framework/simplified_policy/'>
            {' '}
            documentation{' '}
          </a>
          for more information.
          <br />
          <br />
          Information on this page may be up to 8 hours out of date. Please note
          this is a beta feature. We would appreciate your feedback and ideas
          for improvement.
        </Header.Subheader>
      </Header>
      <Tab
        menu={{ secondary: true, pointing: true }}
        panes={panes}
        onTabChange={setActivePane}
      />
      <Divider horizontal />
      {activePaneText === 'Simplified Policy, excluding Unused Permissions' ? (
        <>
          <Grid columns={1} centered>
            <Grid.Row>
              <Grid.Column textAlign='right'>
                <Button
                  primary
                  icon='send'
                  content={
                    'Request Simplified Policy with Unused Permissions Removed'
                  }
                  onClick={onEffectivePolicySubmit}
                  disabled={
                    !resourceEffectivePermissions?.effective_policy_unused_permissions_removed ||
                    !!error
                  }
                />
              </Grid.Column>
            </Grid.Row>
          </Grid>
          <JustificationModal
            handleSubmit={handleEffectivePolicySubmit}
            showDetachManagedPolicy={true}
          />
        </>
      ) : null}
      {activePaneText === 'Simplified Policy' ? (
        <>
          <Grid columns={1} centered>
            <Grid.Row>
              <Grid.Column textAlign='right'>
                <Button
                  primary
                  icon='send'
                  content={'Request Simplified Policy'}
                  onClick={onSimplifedPolicySubmit}
                  disabled={
                    !resourceEffectivePermissions?.effective_policy || !!error
                  }
                />
              </Grid.Column>
            </Grid.Row>
          </Grid>
          <JustificationModal
            handleSubmit={handleEffectivePolicySubmit}
            showDetachManagedPolicy={true}
          />
        </>
      ) : null}
    </>
  )
}

export default EffectivePermissions
