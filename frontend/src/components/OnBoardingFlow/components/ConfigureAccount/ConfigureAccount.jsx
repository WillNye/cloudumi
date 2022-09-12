import React from 'react'
import { useState } from 'react'
import { Accordion, Icon, Table } from 'semantic-ui-react'

const ConfigureAccount = () => {
  const [showComparison, setShowComparison] = useState(false)

  return (
    <div>
      <Table>
        <Table.Header>
          <Table.Row>
            <Table.HeaderCell>
              {/* <Accordion>

                <Accordion.Title
                  active={showComparison}
                  //   index={0}
                    onClick={() => setShowComparison(!showComparison)}
                >
                  <Icon name='dropdown' />
                  What is a dog?
                </Accordion.Title>
        </Accordion> */}
              Status
            </Table.HeaderCell>
            <Table.HeaderCell>Status</Table.HeaderCell>
            <Table.HeaderCell>Notes</Table.HeaderCell>
          </Table.Row>
        </Table.Header>
        {/* <Accordion> */}
        <Table.Body>
          {/* <Accordion.Content active={false}> */}
          <Table.Row>
            <Table.Cell>Jamie</Table.Cell>
            <Table.Cell>Approved</Table.Cell>
            <Table.Cell>Requires call</Table.Cell>
          </Table.Row>
          <Table.Row>
            <Table.Cell>John</Table.Cell>
            <Table.Cell>Selected</Table.Cell>
            <Table.Cell>None</Table.Cell>
          </Table.Row>
          <Table.Row>
            <Table.Cell>Jamie</Table.Cell>
            <Table.Cell>Approved</Table.Cell>
            <Table.Cell>Requires call</Table.Cell>
          </Table.Row>
          <Table.Row>
            <Table.Cell>Jill</Table.Cell>
            <Table.Cell>Approved</Table.Cell>
            <Table.Cell>None</Table.Cell>
          </Table.Row>
          {/* </Accordion.Content> */}
        </Table.Body>

        {/* </Accordion> */}
      </Table>
    </div>
  )
}

export default ConfigureAccount
