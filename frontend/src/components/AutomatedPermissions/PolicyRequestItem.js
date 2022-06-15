import React, { useState } from 'react'
import camelCase from 'lodash/camelCase'
import startCase from 'lodash/startCase'
import {
  Table,
  Segment,
  Header,
  Grid,
  Button,
  Accordion,
} from 'semantic-ui-react'
import { removePolicyRequest, approvePolicyRequest } from './utils'
import Editor from '@monaco-editor/react'
import { APPLIED_POLICY_STATUSES, editorOptions } from './constants'

const PolicyRequestItem = ({
  policyRequest,
  getAutomaticPermissionsRequets,
  sendRequestCommon,
}) => {
  const [isLoading, setIsLoading] = useState(false)
  const [isActive, setIsActive] = useState(false)

  const cantEditPolicy = APPLIED_POLICY_STATUSES.includes(policyRequest.status)

  const approveAutomaticPolicyRequest = async (accountId, policyId) => {
    setIsLoading(true)
    const resJson = await approvePolicyRequest(
      sendRequestCommon,
      accountId,
      policyId
    )

    if (resJson && resJson.id) {
      await getAutomaticPermissionsRequets()
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
      await getAutomaticPermissionsRequets()
    }
    setIsLoading(false)
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
            <Table.Cell>{policyRequest.role || ''}</Table.Cell>
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

      <Accordion>
        <Accordion.Title
          active={isActive}
          onClick={() => setIsActive(!isActive)}
          content='View Generated Policy'
        ></Accordion.Title>
        <Accordion.Content active={isActive}>
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
                        value={JSON.stringify(
                          policyRequest.policy || {},
                          null,
                          '\t'
                        )}
                        onChange={() => {}}
                        options={editorOptions}
                        // onMount={handleEditorDidMount}
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
                      disabled={true}
                      onClick={() => {}}
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
        </Accordion.Content>
      </Accordion>
    </Segment>
  )
}

export default PolicyRequestItem
