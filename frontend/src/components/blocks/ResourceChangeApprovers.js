import React, { useState } from 'react'
import { Grid, Table, Icon, Accordion } from 'semantic-ui-react'

const ResourceChangeApprovers = ({ allowedAdmins }) => {
  const [showAllowedAdmins, setShowAllowedAdmins] = useState(false)

  if (!allowedAdmins.length) {
    return <React.Fragment />
  }

  return (
    <Grid.Row>
      <Grid.Column>
        <Accordion>
          <Accordion.Title
            active={showAllowedAdmins}
            onClick={() => setShowAllowedAdmins(!showAllowedAdmins)}
          >
            <Icon name='dropdown' />
            {!showAllowedAdmins ? 'Show Approvers' : 'Hide Approvers'}
          </Accordion.Title>
          <Accordion.Content active={showAllowedAdmins}>
            <Table celled>
              <Table.Header>
                <Table.Row>
                  <Table.HeaderCell>User/Group</Table.HeaderCell>
                  <Table.HeaderCell>Can Approve</Table.HeaderCell>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {allowedAdmins.map((userGroup, index) => (
                  <Table.Row key={index}>
                    <Table.Cell>{userGroup}</Table.Cell>
                    <Table.Cell positive>
                      <Icon name='checkmark' />
                    </Table.Cell>
                  </Table.Row>
                ))}
              </Table.Body>
            </Table>
          </Accordion.Content>
        </Accordion>
      </Grid.Column>
    </Grid.Row>
  )
}

export default ResourceChangeApprovers
