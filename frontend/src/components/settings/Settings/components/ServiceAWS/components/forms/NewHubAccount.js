/* eslint-disable max-len */
import React, { useContext } from 'react'
import { ApiContext } from 'hooks/useApi'

import { Button, Segment } from 'semantic-ui-react'

export const NewHubAccount = ({ closeModal }) => {
  const aws = useContext(ApiContext)

  const handleClick = () => {
    window.open(aws.data?.central_account_role?.cloudformation_url, '_blank')
    closeModal()
  }

  const isIneligible = aws.data?.central_account_role?.status === 'ineligible'

  return (
    <Segment basic>
      {isIneligible ? (
        <p style={{ textAlign: 'center' }}>
          INELIGIBLE! You cannot connect your account, please ask to your admin
          to help.
        </p>
      ) : (
        <>
          <p style={{ textAlign: 'center' }}>
            Your hub role is Noq’s entrypoint into your environment. Whenever
            Noq attempts to gather information about your resources, update your
            resources, or broker credentials to your roles, it will first access
            your hub account with an external ID that is unique to your
            organization. Your hub account is an AWS account of your choosing
            that will be the entrypoint for Noq into your environment. Our
            onboarding process will walk you through the process of creating
            this role.
          </p>
          <ol>
            <li>
              Authenticate to the AWS account that you want to use as the Hub
              Account.
            </li>
            <li>
              Start the process by clicking the Execute CloudFormation
              button.&nbsp; This will open up a Cloudformation stack in a new
              tab.
            </li>
            <li>
              Execute the Cloudformation, and revisit this page after it has
              successfully executed.
            </li>
          </ol>
          <Button onClick={handleClick} fluid positive>
            Execute CloudFormation
          </Button>
        </>
      )}
    </Segment>
  )
}
