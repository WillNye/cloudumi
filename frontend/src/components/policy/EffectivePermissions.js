import React, { useState } from 'react'
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
import { ReadOnlyPolicyMonacoEditor } from './PolicyMonacoEditor'

const EffectivePermissions = () => {
  const [error, setError] = useState(null)
  const [messages, setMessages] = useState([])
  const {
    resourceEffectivePermissions,
    handleEffectivePolicySubmit,
    setModalWithAdminAutoApprove,
  } = useEffectivePermissions()

  const onLintError = (lintErrors) => {
    if (lintErrors.length > 0) {
      setError(true)
      setMessages(JSON.stringify(lintErrors))
    } else {
      setError(false)
      setMessages([])
    }
  }

  const onEffectivePolicySubmit = () => {
    setModalWithAdminAutoApprove(false)
  }

  const panes = [
    {
      menuItem: 'Effective and Unused Permissions',
      render: () => (
        <Tab.Pane attached={false}>
          <>
            <Header as='h2'>
              Effective Permissions
              <Header.Subheader>
                The effective permissions of a role are a combination of the
                permissions contained in a role's inline policies and managed
                policies. The effective permissions are de-duplicated,
                minimized, and alphabetically sorted. This policy shows all
                permissions removed if they have not been used in the last 90
                days.
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
                  {resourceEffectivePermissions.effective_policy !==
                  resourceEffectivePermissions.effective_policy_unused_permissions_removed ? (
                    <MonacoDiffComponent
                      renderSideBySide={false}
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
                      enableJSON={true}
                      enableTerraform={false}
                      enableCloudFormation={false}
                    />
                  ) : (
                    <ReadOnlyPolicyMonacoEditor
                      onLintError={onLintError}
                      policy={JSON.stringify(
                        resourceEffectivePermissions.effective_policy,
                        null,
                        2
                      )}
                    />
                  )}
                </>
              ) : null}
            </Segment>
          </>
        </Tab.Pane>
      ),
    },
    {
      menuItem: 'Remove Unused Permissions With AWS CLI',
      render: () => (
        <Tab.Pane attached={false}>
          <ReadOnlyPolicyMonacoEditor
            policy={resourceEffectivePermissions?.permission_removal_commands?.aws_cli_script.replace(
              '\n',
              '\r\n'
            )}
            json={false}
            defaultLanguage={'shell'}
          />
        </Tab.Pane>
      ),
    },
    {
      menuItem: 'Remove Unused Permissions With Python',
      render: () => (
        <Tab.Pane attached={false}>
          <ReadOnlyPolicyMonacoEditor
            policy={
              resourceEffectivePermissions?.permission_removal_commands
                ?.python_boto3_script
            }
            json={false}
            defaultLanguage={'python'}
          />
        </Tab.Pane>
      ),
    },
  ]

  // TODO: Give the user commands to do this manually
  return (
    <>
      <Tab menu={{ secondary: true, pointing: true }} panes={panes} />
      <Divider horizontal />
      <Grid columns={1} centered>
        <Grid.Row>
          <Grid.Column textAlign='center'>
            <Button
              primary
              icon='send'
              content='Request Condense Policy and Remove Unused Permissions'
              onClick={onEffectivePolicySubmit}
              disabled={
                !resourceEffectivePermissions?.effective_policy_unused_permissions_removed
              }
            />
          </Grid.Column>
        </Grid.Row>
      </Grid>
      <JustificationModal
        handleSubmit={handleEffectivePolicySubmit}
        showDetachManagedPolicy
      />
    </>
  )
}

export default EffectivePermissions
