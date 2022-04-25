import { ReadOnlyPolicyMonacoEditor } from 'components/policy/PolicyMonacoEditor'
import React from 'react'
import { Table, Segment, Dimmer, Loader, Header } from 'semantic-ui-react'

const GeneratePermissions = () => {
  return (
    <div>
      <Segment placeholder vertical>
        <Dimmer active inverted>
          <Loader size='massive'>
            <p className='loader-text'>
              <b> Detected Access Denied Error</b>
              <br />
              <b> Retrying with permission ...</b>
            </p>
          </Loader>
        </Dimmer>
      </Segment>

      <Segment basic>
        <Table celled striped definition>
          <Table.Body>
            <Table.Row>
              <Table.Cell width={4}>Account</Table.Cell>
              <Table.Cell> </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Amazon Resource Name</Table.Cell>
              <Table.Cell></Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Resource type</Table.Cell>
              <Table.Cell></Table.Cell>
            </Table.Row>

            <Table.Row>
              <Table.Cell>Resource name</Table.Cell>
              <Table.Cell></Table.Cell>
            </Table.Row>

            <Table.Row>
              <Table.Cell>Description</Table.Cell>
              <Table.Cell></Table.Cell>
            </Table.Row>

            <Table.Row>
              <Table.Cell>Event Time</Table.Cell>
              <Table.Cell></Table.Cell>
            </Table.Row>

            <Table.Row>
              <Table.Cell>Created on</Table.Cell>
              <Table.Cell></Table.Cell>
            </Table.Row>

            <Table.Row>
              <Table.Cell>Last Updated</Table.Cell>
              <Table.Cell></Table.Cell>
            </Table.Row>
          </Table.Body>
        </Table>
      </Segment>

      <Segment textAlign='center'>
        <Header as='h3'>Generated Policy</Header>

        <ReadOnlyPolicyMonacoEditor
          policy={{
            Statement: [
              {
                Action: ['s3:getobject', 's3:listbucket'],
                Effect: 'Allow',
                Resource: [
                  'arn:aws:s3:::noq-dev-test-bucket',
                  'arn:aws:s3:::noq-dev-test-bucket/*',
                ],
              },
            ],
          }}
        />
      </Segment>
    </div>
  )
}

export default GeneratePermissions
