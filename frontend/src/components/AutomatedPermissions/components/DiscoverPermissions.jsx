import React from 'react'
import { Segment, Loader, Divider, Header } from 'semantic-ui-react'
import AutomaticPermissionsList from '../AutomaticPermissionsList'

const DiscoverPermissions = ({ policyRequests }) => {
  return (
    <>
      <Segment size='massive' basic>
        <Divider horizontal />
        <Loader active size='massive'>
          <p className='loader-text'>
            <b> Listening for Access Denied errors</b>
          </p>
        </Loader>
        <Divider horizontal />
      </Segment>
      <div className='description-text'>
        <p>
          Configure Weep to run in proxy mode to automatically detect, generate,
          and request policies to resolve Access Denied errors.
        </p>
        <p>
          If the requested permissions are within your organization's risk
          tolerance, they will be automatically approved and applied to the
          role, and Weep will transparently retry the request without ever
          return an access denied error.
        </p>
      </div>
      <Divider />

      <Segment>
        <Header as='h3' block textAlign='center'>
          Generated Policy Requests
        </Header>

        {policyRequests.map((policyRequest) => (
          <AutomaticPermissionsList policyRequest={policyRequest} />
        ))}
      </Segment>
    </>
  )
}

export default DiscoverPermissions
