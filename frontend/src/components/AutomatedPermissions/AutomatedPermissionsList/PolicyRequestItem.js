import React, { useState } from 'react'
import {
  Accordion,
  List,
  Button,
  Label,
  Divider,
  Table,
  Card,
  Segment,
} from 'semantic-ui-react'
import ReactJson from 'react-json-view'
import { Link } from 'react-router-dom'
import { removePolicyRequest, approvePolicyRequest } from '../utils'

const PolicyRequestItem = ({
  policyRequest,
  getAutomaticPermissionsRequets,
  sendRequestCommon,
}) => {
  const [isActive, setIsActive] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const approveAutomaticPolicyRequest = async (accountId, policyId) => {
    setIsLoading(true)
    const resJson = await approvePolicyRequest(
      sendRequestCommon,
      accountId,
      policyId
    )

    if (resJson && resJson.status_code === 200) {
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
    <Card fluid>
      <Segment loading={isLoading}>
        <Card.Content>
          <List.Item>
            <List.Content floated='left'>
              <Card.Header as='h4'>
                <Link
                  to={`automated_permissions/${policyRequest.account.account_id}/${policyRequest.id}`}
                >
                  Access Denied: {policyRequest.account.name}
                </Link>
              </Card.Header>
            </List.Content>
            <List.Content floated='right'>
              <Label
                size='small'
                color={policyRequest.status === 'approved' ? 'green' : 'blue'}
              >
                {policyRequest.status}
              </Label>
            </List.Content>
          </List.Item>
          <Divider horizontal />

          <Table basic='very'>
            <Table.Body>
              <Table.Row>
                <Table.Cell collapsing>arn</Table.Cell>
                <Table.Cell>
                  <div className='break-all'>{policyRequest.role}</div>
                </Table.Cell>
              </Table.Row>
              <Table.Row>
                <Table.Cell>Account</Table.Cell>
                <Table.Cell>{policyRequest.account.account_name}</Table.Cell>
              </Table.Row>
              <Table.Row>
                <Table.Cell>Account Number</Table.Cell>
                <Table.Cell>{policyRequest.account.account_id}</Table.Cell>
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
              <ReactJson
                displayDataTypes={false}
                displayObjectSize={false}
                collapseStringsAfterLength={50}
                indentWidth={4}
                name={false}
                src={policyRequest.policy}
              />
            </Accordion.Content>
          </Accordion>
        </Card.Content>
        <Card.Content>
          <List.Item>
            <List.Content floated='left'>
              <div>Requested By: {policyRequest.user}</div>
              <p>
                Created:&nbsp;
                {policyRequest.event_time &&
                  new Date(policyRequest.event_time).toUTCString()}
              </p>
            </List.Content>
            <List.Content floated='right'>
              <Button.Group size='tiny'>
                <Button
                  color='green'
                  onClick={() =>
                    approveAutomaticPolicyRequest(
                      policyRequest.account.account_id,
                      policyRequest.id
                    )
                  }
                  disabled={policyRequest.status === 'approved'}
                >
                  Approve
                </Button>
                <Button.Or />
                <Button
                  negative
                  onClick={() =>
                    deletePolicyRequest(
                      policyRequest.account.account_id,
                      policyRequest.id
                    )
                  }
                >
                  Remove
                </Button>
              </Button.Group>
            </List.Content>
          </List.Item>
        </Card.Content>
      </Segment>
    </Card>
  )
}

export default PolicyRequestItem
