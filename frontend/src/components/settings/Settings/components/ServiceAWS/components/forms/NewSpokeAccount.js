/* eslint-disable max-len */
import React, { useContext } from 'react'
import { ApiContext, useApi } from 'hooks/useApi'

import { Button, Form, Segment } from 'semantic-ui-react'
import { Bar, Fill } from 'lib/Misc'
import { useCopyToClipboard } from 'hooks/useCopyToClipboard'
import { useForm } from 'react-hook-form'
import { DimmerWithStates } from 'lib/DimmerWithStates'

export const NewSpokeAccount = ({ closeModal, onFinish, defaultValues }) => {

  const { register, handleSubmit, watch } = useForm({ defaultValues })

  const { post } = useApi('services/aws/account/spoke')

  const onSubmit = (data) => {
    post.do(data).then(() => {
      closeModal()
      onFinish()
    })
  }

  const fields = watch()

  const { CopyButton } = useCopyToClipboard()

  const aws = useContext(ApiContext)

  const handleClick = () => {
    window.open(aws.data?.spoke_account_role?.cloudformation_url, '_blank')
    closeModal()
  }

  const isIneligible = aws.data?.spoke_account_role?.status === 'ineligible'

  const isReady = fields.name !== ''

  const isWorking = post?.status === 'working'

  const isSuccess = post?.status === 'done' && !post?.error

  const hasError = post?.error && post?.status === 'done'

  if (defaultValues) return (
    <Segment basic>
      <DimmerWithStates
        loading={isWorking}
        showMessage={hasError}
        messageType={isSuccess ? 'success' : 'warning'}
        message={'Something went wrong, try again!'}
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
          You cannot connect your Spoke Accounts before having a Hub Account
          connected.
        </p>
      ) : (
        <>
          <p style={{ textAlign: 'center' }}>
            Your spoke accounts are all of the AWS accounts that you want to use
            Noq in. We will help you create spoke roles on these accounts. Noq
            will access these roles by first assuming your central ("hub")
            account role and then assuming the spoke role in the target account.
            For example, assume that a customer has configured Noq's central
            role on *account_a*. They've configured spoke roles on *account_a*
            and *account_b* (Yes, the central account must also have a spoke
            role if you want Noq to work on it). If Noq needs to write a policy
            to an IAM role on *account_b*, it will assume the central role on
            *account_a* with an external ID that is unique to your organization,
            and then it will assume the spoke role on *account_b*. It will write
            the IAM policy from the spoke role on *account_b*.
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
