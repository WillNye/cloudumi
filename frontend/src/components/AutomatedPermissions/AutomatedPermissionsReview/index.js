import React, { useEffect, useState } from 'react'
import camelCase from 'lodash/camelCase'
import startCase from 'lodash/startCase'
import { useHistory, useRouteMatch } from 'react-router-dom'
import { ReadOnlyPolicyMonacoEditor } from 'components/policy/PolicyMonacoEditor'
import {
  Table,
  Segment,
  Dimmer,
  Loader,
  Header,
  Divider,
  Grid,
  Button,
} from 'semantic-ui-react'
import { useAuth } from '../../../auth/AuthProviderDefault'
import NoMatch from 'components/NoMatch'
import { removePolicyRequest, approvePolicyRequest } from '../utils'

const AutomatedPermissionsReview = () => {
  const match = useRouteMatch()
  const history = useHistory()
  const { sendRequestCommon } = useAuth()

  const [automatedPolicy, setAutomatedPolicy] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(false)

  const getPolicyRequest = async () => {
    const params = match.params
    const res = await sendRequestCommon(
      null,
      `/api/v3/automatic_policy_request_handler/aws/${params.accountId}/${params.policyId}`,
      'get'
    )

    if (res && res.data) {
      setAutomatedPolicy(res.data)
    } else {
      setError(true)
    }
    setIsLoading(false)
  }

  useEffect(() => {
    setIsLoading(true)
    getPolicyRequest().then()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const approveAutomaticPolicyRequest = async (accountId, policyId) => {
    setIsLoading(true)
    const resJson = await approvePolicyRequest(
      sendRequestCommon,
      accountId,
      policyId
    )

    if (resJson && resJson.status_code === 200) {
      await getPolicyRequest()
    }
    setIsLoading(false)
  }

  const deletePolicyRequest = async (accountId, policyId) => {
    setIsLoading(true)
    const resJson = await removePolicyRequest(
      sendRequestCommon,
      accountId,
      policyId
    )

    if (resJson && resJson.status_code === 200) {
      history.push('/automated_permissions')
    }
    setIsLoading(false)
  }

  if (isLoading) {
    return (
      <Dimmer active page>
        <Loader active inline='centered' size='large'>
          <Divider horizontal />
          Loading ...
        </Loader>
      </Dimmer>
    )
  }

  if (error) {
    return <NoMatch />
  }

  return (
    <div>
      <Segment>
        <Table celled striped definition>
          <Table.Body>
            <Table.Row>
              <Table.Cell width={4}>Status</Table.Cell>
              <Table.Cell>
                {startCase(camelCase(automatedPolicy.status || ''))}
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Role</Table.Cell>
              <Table.Cell>{automatedPolicy.role || ''}</Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Role Owner</Table.Cell>
              <Table.Cell>{automatedPolicy.role_owner || ''}</Table.Cell>
            </Table.Row>

            <Table.Row>
              <Table.Cell>User</Table.Cell>
              <Table.Cell>{automatedPolicy.user || ''}</Table.Cell>
            </Table.Row>

            <Table.Row>
              <Table.Cell>Event Time</Table.Cell>
              <Table.Cell>
                {automatedPolicy.event_time
                  ? new Date(automatedPolicy.event_time).toUTCString()
                  : ''}
              </Table.Cell>
            </Table.Row>

            <Table.Row>
              <Table.Cell>Access Denied Error</Table.Cell>
              <Table.Cell>{automatedPolicy.error || ''}</Table.Cell>
            </Table.Row>

            <Table.Row>
              <Table.Cell>Last Updated</Table.Cell>
              <Table.Cell>
                {automatedPolicy.last_updated
                  ? new Date(automatedPolicy.last_updated).toUTCString()
                  : ''}
              </Table.Cell>
            </Table.Row>
          </Table.Body>
        </Table>
      </Segment>
      <Segment>
        <div className='center-icons'>
          <Header as='h3' className='padded'>
            Generated Policy
          </Header>
          <Grid>
            <Grid.Row>
              <Grid.Column>
                <ReadOnlyPolicyMonacoEditor
                  policy={automatedPolicy.policy || {}}
                />
              </Grid.Column>
            </Grid.Row>
            <Grid.Row columns='equal'>
              <Grid.Column>
                <Button
                  content='Apply Change'
                  positive
                  fluid
                  disabled={automatedPolicy.status === 'approved'}
                  onClick={() =>
                    approveAutomaticPolicyRequest(
                      automatedPolicy.account.account_id,
                      automatedPolicy.id
                    )
                  }
                />
              </Grid.Column>
              <Grid.Column>
                <Button
                  content='Remove'
                  negative
                  fluid
                  onClick={() =>
                    deletePolicyRequest(
                      automatedPolicy.account.account_id,
                      automatedPolicy.id
                    )
                  }
                />
              </Grid.Column>
            </Grid.Row>
          </Grid>
        </div>
      </Segment>
    </div>
  )
}

export default AutomatedPermissionsReview
