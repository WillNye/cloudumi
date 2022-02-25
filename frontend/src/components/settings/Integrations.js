import React from 'react'
import { Segment } from 'semantic-ui-react'

export const Integrations = () => {
  return (
    <Segment>
      Add AWS Integration Pops up a Modal and runs cloudformation stack with
      unique external ID Calls back to Noq with unique external ID and some
      validation nonce We verify nonce and add integration to user's thing. Add
      RepoKid to one or more of your accounts Add AWS SSO Integration? Add
      Identity management Okta, Google, Microsoft, etc. Add Google Keys - For
      getting google group membership Add Slack Webhook URLs or Slack Webhook
      URL Generation logic Logging? Sentry? Sync Settings (Please upgrade to
      sync more than once per day) Do we want to advertise these? On-Prem
      DynamoDB (Enterprise feature) On-Prem S3 (Enterprise feature) On-Prem
      Redis (Enterprise feature) Need Auth settings Need network access
    </Segment>
  )
}
