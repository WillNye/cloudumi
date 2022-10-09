import { MODES } from 'components/OnBoardingFlow/constants'
import React, { Fragment, useState } from 'react'
import { Link } from 'react-router-dom'
import { Divider, Form, Icon, Label, Radio, Table } from 'semantic-ui-react'

const ConfigureAccount = ({
  handleAccNameChange,
  accountName,
  selectedMode,
  handleModeChange,
}) => {
  const [showComparison, setShowComparison] = useState(false)

  return (
    <div className='on-boarding__configure-account'>
      <Form>
        <Form.Field>
          <label>1. Specify AWS Account</label>
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
          <label>2. Select Installation Mode:</label>
        </Form.Field>
        <div className='on-boarding__container'>
          <div style={{ margin: '30px' }}>
            <Form.Field>
              <Radio
                label='Read-Only'
                value={MODES.READ_ONLY}
                checked={selectedMode === MODES.READ_ONLY}
                onChange={handleModeChange}
              />
            </Form.Field>
            <p>
              Cloud Identities and Resources will not be modified in Read-Only
              mode.
            </p>
            <p>
              This mode only grants Noq privileges to inventory Cloud identities
              and IAM policies. Approved requests will require manual changes to
              apply and remove after expiration.
            </p>
          </div>
          <div style={{ margin: '30px' }}>
            <Form.Field>
              <Radio
                label='Read-Write'
                value={MODES.READ_WRTE}
                checked={selectedMode === MODES.READ_WRTE}
                onChange={handleModeChange}
              />
              &nbsp;
              <Label color='green' horizontal>
                <Icon name='star' />
                Recommended
              </Label>
            </Form.Field>
            <p>
              Read-write installation <em>can</em> change Cloud identities or
              alter IAM policies to automate request approval or expiration.
            </p>
            <p>
              This mode grants Noq privileges to inventory and change Cloud
              identities and IAM policies. Changes can only occur when users
              make requests using Noq, and they are approved by an
              administrator. Changes will be applied automatically after
              approval and removed automatically after expiration.
            </p>
          </div>
        </div>
      </Form>

      <Divider horizontal />

      <Table celled>
        <Table.Header>
          <Table.Row>
            <Table.HeaderCell
              onClick={() => setShowComparison(!showComparison)}
            >
              <Icon name={`${showComparison ? 'angle down' : 'angle right'}`} />
              Compare Installation Modes
            </Table.HeaderCell>
            <Table.HeaderCell>Read-Only</Table.HeaderCell>
            <Table.HeaderCell>
              <span>
                Read-Write <Icon name='star' color='green' />
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
                  Broker Credentials
                </Link>
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='x' color='red' />
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Access Roles</Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='x' color='red' />
              </Table.Cell>
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
                  Access Roles Temporarily
                </Link>
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='x' color='red' />
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
                  Grant Permissions Temporarily
                </Link>
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='x' color='red' />
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
                  Self-Service Requests
                </Link>
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <div className='on-boarding__configure-account-cell'>
                  <Icon name='checkmark' color='green' />
                  <div className='on-boarding__configure-account-cell-text'>
                    Manual
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
                  to='/docs/features/resource_management/create_role/'
                  target='_blank'
                  rel='noopener noreferrer'
                >
                  Create Roles
                </Link>
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='x' color='red' />
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
                  Remove Unused Permissions
                </Link>
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <div className='on-boarding__configure-account-cell'>
                  <Icon name='checkmark' color='green' />
                  <div className='on-boarding__configure-account-cell-text'>
                    Manual
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
                  Delegate Viewers
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
                  to='/docs/features/permissions_management_and_request_framework/decentralized_request_management/'
                  target='_blank'
                  rel='noopener noreferrer'
                >
                  Delegate Adminstrators
                </Link>
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='x' color='red' />
              </Table.Cell>
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
                  Automate Low-Risk Approval
                </Link>
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='x' color='red' />
              </Table.Cell>
              <Table.Cell textAlign='center'>
                <Icon name='checkmark' color='green' />
              </Table.Cell>
            </Table.Row>
            <Table.Row>
              <Table.Cell>Review Resource History</Table.Cell>
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
          </Table.Body>
        ) : (
          <Fragment />
        )}
      </Table>
    </div>
  )
}

export default ConfigureAccount
