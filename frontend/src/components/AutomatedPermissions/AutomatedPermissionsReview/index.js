import React, { useEffect, useState } from 'react'
import camelCase from 'lodash/camelCase'
import startCase from 'lodash/startCase'
import { useRouteMatch } from 'react-router-dom'
import { ReadOnlyPolicyMonacoEditor } from 'components/policy/PolicyMonacoEditor'
import {
  Table,
  Segment,
  Dimmer,
  Loader,
  Header,
  Divider,
} from 'semantic-ui-react'
import { useAuth } from '../../../auth/AuthProviderDefault'
import NoMatch from 'components/NoMatch'

const AutomatedPermissionsReview = () => {
  const [automatedPolicy, setAutomatedPolicy] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(false)

  const match = useRouteMatch()
  const { sendRequestCommon } = useAuth()

  useEffect(() => {
    setIsLoading(true)
    const params = match.params
    sendRequestCommon(
      null,
      `/api/v3/automatic_policy_request_handler/aws/${params.accountId}/${params.policyId}`,
      'get'
    )
      .then((res) => {
        if (res && res.data) {
          setAutomatedPolicy(res.data)
        } else {
          setError(true)
        }
        setIsLoading(false)
      })
      .catch(() => {
        setError(true)
        setIsLoading(false)
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

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
          {/* <div className='monaco-editor'> */}
          <ReadOnlyPolicyMonacoEditor policy={automatedPolicy.policy || {}} />
          {/* </div> */}
        </div>
      </Segment>
    </div>
  )
}

export default AutomatedPermissionsReview
