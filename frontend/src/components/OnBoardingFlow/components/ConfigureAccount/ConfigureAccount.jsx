import React, { Fragment, useState } from 'react'
import { Divider, Form, Icon, Label, Radio, Table } from 'semantic-ui-react'

const ConfigureAccount = () => {
  const [showComparison, setShowComparison] = useState(false)

  return (
    <div className='on-boarding__configure-account'>
      <Form>
        <Form.Field>
          <label>1. AWS Account Name</label>
          <input placeholder='Enter AWS Account Name' />
        </Form.Field>
        <Divider horizontal />

        <Form.Field>
          <label>2. Select mode:</label>
        </Form.Field>
        <div className='on-boarding__container'>
          <div>
            <Form.Field>
              <Radio label='Read-only' />
            </Form.Field>
            <p>
              Lorem ipsum copy placeholder which is a short description of the
              functionality summarized.
            </p>
          </div>
          <div>
            <Form.Field>
              <Radio label='Read-write' checked />
              &nbsp;
              <Label color='green' horizontal>
                <Icon name='star outline' />
                Recommended
              </Label>
            </Form.Field>
            <p>
              Lorem ipsum copy placeholder which is a short description of the
              functionality summarized.
            </p>
          </div>
        </div>

        <Divider horizontal />
      </Form>

      <Table celled>
        <Table.Header>
          <Table.Row>
            <Table.HeaderCell
              onClick={() => setShowComparison(!showComparison)}
            >
              <Icon name={`${showComparison ? 'angle down' : 'angle right'}`} />
              Feature Comparison
            </Table.HeaderCell>
            <Table.HeaderCell>Read-only</Table.HeaderCell>
            <Table.HeaderCell>
              <span>
                Read-write <Icon name='star outline' color='green' />
              </span>
            </Table.HeaderCell>
          </Table.Row>
        </Table.Header>
        {showComparison ? (
          <Table.Body>
            <Table.Row>
              <Table.Cell>Credential Brokering</Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Self-service</Table.Cell>
              <Table.Cell textAlign='center'>
                <div className='on-boarding__configure-account-cell'>
                  <Icon name='checkmark' color='green' />
                  <div className='on-boarding__configure-account-cell-text'>
                    Limited
                  </div>
                </div>
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Unused Permissions Removal</Table.Cell>
              <Table.Cell textAlign='center'>
                <div className='on-boarding__configure-account-cell'>
                  <Icon name='checkmark' color='green' />
                  <div className='on-boarding__configure-account-cell-text'>
                    Limited
                  </div>
                </div>
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Resource History</Table.Cell>
              <Table.Cell textAlign='center'>
                <div className='on-boarding__configure-account-cell'>
                  <Icon name='checkmark' color='green' />
                  <div className='on-boarding__configure-account-cell-text'>
                    Limited
                  </div>
                </div>
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Delegated Resource Viewership</Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Temporary Permissions</Table.Cell>
              <Table.Cell></Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Temporary Escalation</Table.Cell>
              <Table.Cell></Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Low-Risk Auto-Approval</Table.Cell>
              <Table.Cell></Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Delegated Adminstration</Table.Cell>
              <Table.Cell></Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Role Creation/Cloning</Table.Cell>
              <Table.Cell></Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Request Access to a Role</Table.Cell>
              <Table.Cell></Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
          </Table.Body>
        ) : (
          <Fragment />
        )}
      </Table>
    </div>
  )
}

export default ConfigureAccount
