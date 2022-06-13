import React, { useState } from 'react'
import {
  Accordion,
  Icon,
  List,
  Button,
  Label,
  Divider,
  Segment,
  Table,
} from 'semantic-ui-react'
import ReactJson from 'react-json-view'

const AutomaticPermissionsList = ({ policyRequest }) => {
  console.log(policyRequest, '++++++++++++++++++++======================')
  const [isActive, setIsActive] = useState(false)

  return (
    <Segment>
      <List>
        <List.Item>
          <List.Content>
            <List.Header as='h4'>
              {policyRequest.role}
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
              <Label
                size='small'
                color={policyRequest.status === 'approved' ? 'green' : 'blue'}
              >
                {policyRequest.status}
              </Label>
            </List.Header>
            <Table basic='very'>
              <Table.Body>
                {/* <Table.Row>
                    <Table.Cell collapsing>arn</Table.Cell>
                    <Table.Cell>{policyRequest.role}</Table.Cell>
                  </Table.Row> */}
                {/* <Table.Row>
                    <Table.Cell>Status</Table.Cell>
                    <Table.Cell>
                      <Label
                        size='small'
                        color={
                          policyRequest.status === 'approved' ? 'green' : 'blue'
                        }
                      >
                        {policyRequest.status}
                      </Label>
                    </Table.Cell>
                  </Table.Row> */}
                {/* <Table.Row>
                    <Table.Cell>Requester</Table.Cell>
                    <Table.Cell>{policyRequest.user}</Table.Cell>
                  </Table.Row> */}
              </Table.Body>
            </Table>
          </List.Content>
        </List.Item>

        {/* <Divider horizontal /> */}

        <List.Item>
          <List.Content>
            <Accordion>
              <Accordion.Title
                as='h1'
                active={isActive}
                onClick={() => setIsActive(!isActive)}
                content={<Label content='View Generated Policy' />}
              ></Accordion.Title>
              <Accordion.Content active={isActive}>
                <Divider />

                <ReactJson
                  displayDataTypes={false}
                  displayObjectSize={false}
                  collapseStringsAfterLength={50}
                  indentWidth={4}
                  name={false}
                  src={policyRequest.policy}
                />
                <Divider />
              </Accordion.Content>
            </Accordion>
          </List.Content>
        </List.Item>

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
              <Button color='green'>Approve</Button>
              <Button.Or />
              <Button color='red'>Remove</Button>
            </Button.Group>
          </List.Content>
        </List.Item>
        {/* </List.Item> */}
      </List>
    </Segment>
  )
}

export default AutomaticPermissionsList
