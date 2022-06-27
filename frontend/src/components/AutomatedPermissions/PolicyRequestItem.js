import React, { useCallback, useMemo, useState } from 'react'
import camelCase from 'lodash/camelCase'
import startCase from 'lodash/startCase'
import {
  Table,
  Segment,
  Header,
  Grid,
  Button,
  Form,
  Search,
} from 'semantic-ui-react'
import {
  removePolicyRequest,
  approvePolicyRequest,
  updatePolicyRequest,
} from './utils'
import Editor from '@monaco-editor/react'
import { useToast } from 'lib/Toast'
import { APPLIED_POLICY_STATUSES, editorOptions } from './constants'

const PolicyRequestItem = ({
  policyRequest,
  getAutomaticPermissionsRequets,
  sendRequestCommon,
}) => {
  const [isLoading, setIsLoading] = useState(false)
  const [results, setResults] = useState([])
  const [rolevalue, setRoleValue] = useState(policyRequest.role || '')

  const { error, success } = useToast()

  const existingPolicy = JSON.stringify(policyRequest.policy || {}, null, '\t')
  const [modifiedPolicy, setModifiedPolicy] = useState(existingPolicy)

  const noChangesDetected = useMemo(
    () => existingPolicy === modifiedPolicy,
    [existingPolicy, modifiedPolicy]
  )

  const cantEditPolicy = APPLIED_POLICY_STATUSES.includes(policyRequest.status)

  const getAllRoles = (value) => {
    const TYPEAHEAD_API = `/api/v2/typeahead/self_service_resources?typeahead=${value}`
    sendRequestCommon(null, TYPEAHEAD_API, 'get').then((results) => {
      const reformattedResults = results.map((res, idx) => {
        return {
          id: idx,
          title: res.display_text,
          ...res,
        }
      })
      setResults(reformattedResults)
    })
  }

  const handleSearch = (_event, { value }) => {
    setRoleValue(value)
    getAllRoles(value)
  }

  const handleResultSelect = useCallback(
    (_e, { result }) => {
      const value = result?.principal?.principal_arn || policyRequest.role
      handleUpdateRequest(policyRequest.account.account_id, policyRequest.id, {
        role: value,
        policy: JSON.parse(modifiedPolicy),
      })
    },
    [modifiedPolicy, policyRequest] // eslint-disable-line react-hooks/exhaustive-deps
  )

  const approveAutomaticPolicyRequest = (accountId, policyId) => {
    setIsLoading(true)
    approvePolicyRequest(sendRequestCommon, accountId, policyId)
      .then(() => {
        getAutomaticPermissionsRequets().then()
        success('Request successfully approved')
      })
      .catch(() => {
        error('Unable to approve request')
      })
      .finally(() => {
        setIsLoading(false)
      })
  }

  const deletePolicyRequest = (accountId, policyId) => {
    setIsLoading(true)
    removePolicyRequest(sendRequestCommon, accountId, policyId)
      .then(() => {
        getAutomaticPermissionsRequets().then()
        success('Request successfully deleted')
      })
      .catch(() => {
        error('Unable to remove request')
      })
      .finally(() => {
        setIsLoading(false)
      })
  }

  const handleUpdateRequest = (accountId, policyId, data) => {
    setIsLoading(true)
    updatePolicyRequest(sendRequestCommon, accountId, policyId, data)
      .then((res) => {
        getAutomaticPermissionsRequets().then()
        success('Request successfully update')
        setRoleValue(res.role)
      })
      .catch(() => {
        setRoleValue(policyRequest.role)
        error('Unable to update request')
      })
      .finally(() => {
        setIsLoading(false)
      })
  }

  return (
    <Segment loading={isLoading}>
      <Table celled striped definition compact>
        <Table.Body>
          <Table.Row>
            <Table.Cell width={4}>Status</Table.Cell>
            <Table.Cell>
              {startCase(camelCase(policyRequest.status || ''))}
            </Table.Cell>
          </Table.Row>
          <Table.Row>
            <Table.Cell>Role</Table.Cell>
            <Table.Cell>
              <Form widths='equal'>
                <Form.Field required>
                  <Search
                    required
                    fluid
                    onResultSelect={handleResultSelect}
                    onSearchChange={handleSearch}
                    results={results}
                    value={rolevalue}
                  />
                </Form.Field>
              </Form>
            </Table.Cell>
          </Table.Row>
          <Table.Row>
            <Table.Cell>Role Owner</Table.Cell>
            <Table.Cell>{policyRequest.role_owner || ''}</Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell>User</Table.Cell>
            <Table.Cell>{policyRequest.user || ''}</Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell>Event Time</Table.Cell>
            <Table.Cell>
              {policyRequest.event_time
                ? new Date(policyRequest.event_time).toUTCString()
                : ''}
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell>Access Denied Error</Table.Cell>
            <Table.Cell>{policyRequest.error || ''}</Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell>Last Updated</Table.Cell>
            <Table.Cell>
              {policyRequest.last_updated
                ? new Date(policyRequest.last_updated).toUTCString()
                : ''}
            </Table.Cell>
          </Table.Row>
        </Table.Body>
      </Table>
      <Segment>
        <div className='center-icons'>
          <Header as='h3' className='padded'>
            Generated Policy
          </Header>
          <Grid>
            <Grid.Row>
              <Grid.Column>
                <Segment
                  attached
                  style={{
                    border: 0,
                    padding: 0,
                  }}
                >
                  <Editor
                    height='450px'
                    defaultLanguage='json'
                    defaultValue={existingPolicy}
                    onChange={(value) => {
                      setModifiedPolicy(value)
                    }}
                    modified={modifiedPolicy}
                    options={{ ...editorOptions, readonly: cantEditPolicy }}
                    alwaysConsumeMouseWheel={false}
                    textAlign='center'
                  />
                </Segment>
              </Grid.Column>
            </Grid.Row>
            <Grid.Row columns='equal'>
              <Grid.Column>
                <Button
                  content='Apply Change'
                  positive
                  fluid
                  disabled={cantEditPolicy}
                  onClick={() =>
                    approveAutomaticPolicyRequest(
                      policyRequest.account.account_id,
                      policyRequest.id
                    )
                  }
                />
              </Grid.Column>
              <Grid.Column>
                <Button
                  content='Update Change'
                  positive
                  fluid
                  disabled={cantEditPolicy || noChangesDetected}
                  onClick={() =>
                    handleUpdateRequest(
                      policyRequest.account.account_id,
                      policyRequest.id,
                      {
                        role: policyRequest.role,
                        policy: JSON.parse(modifiedPolicy),
                      }
                    )
                  }
                />
              </Grid.Column>
              <Grid.Column>
                <Button
                  content='Remove'
                  negative
                  fluid
                  disabled={cantEditPolicy}
                  onClick={() =>
                    deletePolicyRequest(
                      policyRequest.account.account_id,
                      policyRequest.id
                    )
                  }
                />
              </Grid.Column>
            </Grid.Row>
          </Grid>
        </div>
      </Segment>
    </Segment>
  )
}

export default PolicyRequestItem
