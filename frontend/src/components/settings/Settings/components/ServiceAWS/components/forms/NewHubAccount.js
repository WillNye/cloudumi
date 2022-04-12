/* eslint-disable max-len */
import React, { useContext, useState } from 'react'
import { ApiContext, useApi } from 'hooks/useApi'

import { Button, Form, Segment } from 'semantic-ui-react'
import { Bar, Fill } from 'lib/Misc'
import { useCopyToClipboard } from 'hooks/useCopyToClipboard'
import { useForm } from 'react-hook-form'
import { DimmerWithStates } from 'lib/DimmerWithStates'

export const NewHubAccount = ({ closeModal, onFinish, defaultValues }) => {
  const { register, handleSubmit, watch } = useForm({ defaultValues })

  const { post } = useApi('services/aws/account/hub')

  const [errorMessage, setErrorMessage] = useState(
    'Something went wrong, try again!'
  )

  const onSubmit = (data) => {
    post
      .do(data)
      .then(() => {
        closeModal()
        onFinish()
      })
      .catch(({ errorsMap, message }) => {
        setErrorMessage(errorsMap || message)
      })
  }

  const fields = watch()

  const { CopyButton } = useCopyToClipboard()

  const aws = useContext(ApiContext)

  const handleClick = () => {
    window.open(aws.data?.central_account_role?.cloudformation_url, '_blank')
    closeModal()
  }

  const isIneligible = aws.data?.central_account_role?.status === 'ineligible'

  const isReady = fields.name !== ''

  const isWorking = post?.status === 'working'

  const isSuccess = post?.status === 'done' && !post?.error

  const hasError = post?.error && post?.status === 'done'

  if (defaultValues)
    return (
      <Segment basic>
        <DimmerWithStates
          loading={isWorking}
          showMessage={hasError}
          messageType={isSuccess ? 'success' : 'warning'}
          message={errorMessage}
        />

        <Form onSubmit={handleSubmit(onSubmit)}>
          <Form.Field>
            <label>Role Name</label>
            <input {...register('name', { required: true })} />
          </Form.Field>

          <Bar>
            <Fill />
            <Button type='submit' disabled={!isReady} positive>
              Submit
            </Button>
          </Bar>
        </Form>
      </Segment>
    )

  return (
    <Segment basic>
      {isIneligible ? (
        <p style={{ textAlign: 'center' }}>
          Ineligible. You are unable to connect your account, please ask to your
          admin to help.
        </p>
      ) : (
        <>
          <p style={{ textAlign: 'center' }}>
            Your hub role is Noq's entrypoint into your environment. Whenever
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
          <Bar>
            <Button onClick={handleClick} fluid positive>
              Execute CloudFormation
            </Button>
            <CopyButton
              value={aws.data?.central_account_role?.cloudformation_url}
            />
          </Bar>
        </>
      )}
    </Segment>
  )
}
