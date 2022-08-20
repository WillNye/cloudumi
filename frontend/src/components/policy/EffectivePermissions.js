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
      menuItem: 'Simplified Policy',
      render: () => (
        <Tab.Pane attached={false}>
          <>
            <Header as='h2'>
              Simplified Policy
              <Header.Subheader>
                <br />
                This feature allows you to view the simplified policy of your
                identity. Information on this page may be up to 8 hours out of
                date. Please note this is a beta feature. We would appreciate
                your feedback and ideas for improvement.
                <br />
                <br />
                A policy is simplifed by combining all of the identity's inline
                and managed policies into a single policy. Permissions are then
                de-duplicated and alphabetically sorted.
                <br />
                <br />
                This view also utilizes data from Access Advisor to show
                permissions that have not been used in the last 90 days.
                <br />
                <br />
                The button on the bottom allows you to request that the policies
                of this identity be replaced with the simplified policy, with
                unused permissions removed. You will be prompted before a
                justification before the request is created. An administrator,
                or a delegated administrator for the account, will need to
                approve the request before it is applied.
                <br />
                <br />
                After the request is approved, Noq will proceed to add the
                simplified policy to the identity, and then remove all existing
                inline policies and detach managed policies. The removal of
                managed policies is optional. If you would like more control
                over the simplified policy, you may view and utilize the Python
                or AWS CLI versions.
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
                      renderSideBySide={true}
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
                      readOnly={false}
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
      menuItem: 'Simplify Policy with AWS CLI',
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
      menuItem: 'Simplify Policy With Python',
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
              content='Request Condensed Policy with Unused Permissions Removed'
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
