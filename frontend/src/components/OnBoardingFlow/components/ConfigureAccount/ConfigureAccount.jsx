import React, { Fragment, useState } from 'react'
import { Link } from 'react-router-dom'
import { Divider, Form, Icon, Label, Radio, Table } from 'semantic-ui-react'

const MODES = {
  READ_ONLY: 'read-only',
  READ_WRTE: 'read-write',
}

const ConfigureAccount = ({ handleAccNameChange, accountName }) => {
  const [showComparison, setShowComparison] = useState(false)
  const [selectedMode, setSelectedMode] = useState(MODES.READ_WRTE)

  const handleChange = (_e, { value }) => setSelectedMode(value)

  return (
    <div className='on-boarding__configure-account'>
      <Form>
        <Form.Field>
          <label>1. AWS Account Name</label>
          <input
            placeholder='Enter AWS Account Name'
            onChange={handleAccNameChange}
            maxLength='50'
            minLength='1'
            value={accountName}
          />
        </Form.Field>
        <Divider horizontal />

        <Form.Field>
          <label>2. Select mode:</label>
        </Form.Field>
        <div className='on-boarding__container'>
          <div>
            <Form.Field>
              <Radio
                label='Read-only'
                value={MODES.READ_ONLY}
                checked={selectedMode === MODES.READ_ONLY}
                onChange={handleChange}
              />
            </Form.Field>
            <p>
              Lorem ipsum copy placeholder which is a short description of the
              functionality summarized.
            </p>
          </div>
          <div>
            <Form.Field>
              <Radio
                label='Read-write'
                value={MODES.READ_WRTE}
                checked={selectedMode === MODES.READ_WRTE}
                onChange={handleChange}
              />
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
              <Table.Cell>
                <Link
                  to='/docs/getting_started/enable_users_to_assume_roles/'
                  target='_blank'
                  rel='noopener noreferrer'
                >
                  Credential Brokering
                </Link>
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>
                <Link
                  to='/docs/features/permissions_management_and_request_framework/self_service_permissions/'
                  target='_blank'
                  rel='noopener noreferrer'
                >
                  Self-service
                </Link>
              </Table.Cell>
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
              <Table.Cell>
                <Link
                  to='/docs/features/planned/unused_permissions_removal/'
                  target='_blank'
                  rel='noopener noreferrer'
                >
                  Unused Permissions Removal
                </Link>
              </Table.Cell>
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
              <Table.Cell>
                <Link
                  to='/docs/features/permissions_management_and_request_framework/restrict_viewers_of_account_resources/'
                  target='_blank'
                  rel='noopener noreferrer'
                >
                  Delegated Resource Viewership
                </Link>
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>
                <Link
                  to='/docs/features/permissions_management_and_request_framework/temporary_policy_requests/'
                  target='_blank'
                  rel='noopener noreferrer'
                >
                  Temporary Permissions
                </Link>
              </Table.Cell>
              <Table.Cell></Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>
                <Link
                  to='/docs/features/permissions_management_and_request_framework/temporary_role_access/'
                  target='_blank'
                  rel='noopener noreferrer'
                >
                  Temporary Escalation
                </Link>
              </Table.Cell>
              <Table.Cell></Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>
                <Link
                  to='/docs/features/permissions_management_and_request_framework/automatically_approve_low_risk_requests/'
                  target='_blank'
                  rel='noopener noreferrer'
                >
                  Low-Risk Auto-Approval
                </Link>
              </Table.Cell>
              <Table.Cell></Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>
                <Link
                  to='/docs/features/permissions_management_and_request_framework/decentralized_request_management/'
                  target='_blank'
                  rel='noopener noreferrer'
                >
                  Delegated Adminstration
                </Link>
              </Table.Cell>
              <Table.Cell></Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>
                <Link
                  to='/docs/features/resource_management/create_role/'
                  target='_blank'
                  rel='noopener noreferrer'
                >
                  Role Creation/Cloning
                </Link>
              </Table.Cell>
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
