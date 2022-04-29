import React from 'react'
import { Segment, Dimmer, Loader } from 'semantic-ui-react'

const DiscoverPermissions = () => {
  return (
    <>
      <Segment placeholder vertical>
        <Dimmer active inverted>
          <Loader size='massive'>
            <p className='loader-text'>
              <b> Listening for Access Denied errors</b>
            </p>
          </Loader>
        </Dimmer>
      </Segment>
      <Segment className='description-text' basic>
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
      </Segment>
    </>
  )
}

export default DiscoverPermissions
