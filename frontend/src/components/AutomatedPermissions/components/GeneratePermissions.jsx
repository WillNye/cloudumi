import React, { useMemo } from 'react'
import camelCase from 'lodash/camelCase'
import startCase from 'lodash/startCase'
import { ReadOnlyPolicyMonacoEditor } from 'components/policy/PolicyMonacoEditor'
import { Table, Segment, Dimmer, Loader, Header, Icon } from 'semantic-ui-react'

const GeneratePermissions = ({ automatedPolicy }) => {
  const showLoader = useMemo(() => {
    const status = automatedPolicy.status || ''
    if (['applied_and_success', 'applied_and_failure'].includes(status)) {
      return false
    }
    return true
  }, [automatedPolicy])

  const SuccessComponent = (
    <div>
      <Icon size='massive' color='green' name='check circle outline' />
      <p className='loader-text'>
        <b> Request Successful!</b>
        <br />
        <b> Refreshing soon ...</b>
      </p>
    </div>
  )

  const ErrorComponent = (
    <div>
      <Icon size='massive' color='red' name='times circle outline' />
      <p className='loader-text'>
        <b> Unable to apply generate permission</b>
        <br />
        <b> Request permission ...</b>
      </p>
    </div>
  )

  return (
    <div>
      <Segment vertical>
        {showLoader ? (
          <Segment placeholder basic>
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
        ) : (
          <div className='center-icons'>
            {automatedPolicy.status !== 'applied_and_success'
              ? ErrorComponent
              : SuccessComponent}
          </div>
        )}
      </Segment>

      <Segment basic>
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

      <div className='center-icons'>
        <Header as='h3' className='padded'>
          Generated Policy
        </Header>
        <div className='monaco-editor'>
          <ReadOnlyPolicyMonacoEditor policy={automatedPolicy.policy || {}} />
        </div>
      </div>
    </div>
  )
}

export default GeneratePermissions
