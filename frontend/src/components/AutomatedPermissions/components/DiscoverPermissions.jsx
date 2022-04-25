import React from 'react'
import { Segment, Dimmer, Loader } from 'semantic-ui-react'

const DiscoverPermissions = () => {
  return (
    <>
      <Segment placeholder vertical>
        <Dimmer active inverted>
          <Loader size='massive'>
            <p className='loader-text'>
              <b> Listening for access denied error</b>
            </p>
          </Loader>
        </Dimmer>
      </Segment>
      <Segment className='description-text' basic>
        <p>
          When AWS API operations are denied, Noq can propose policy changes to
          grant access.
        </p>

        <p>
          A Weep proxy searches for a policy by retrying those specific
          operations with additional permissions, within the risk tolerance of
          an Organization (see $link).
        </p>

        <p>
          A proposal to add all of those permissions can be displayed for
          review, submitted as a role request, or applied automatically.
        </p>
      </Segment>
    </>
  )
}

export default DiscoverPermissions
