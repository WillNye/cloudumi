/* eslint-disable max-len */
import React, { useContext, useState } from 'react'
import { ApiContext, useApi } from 'hooks/useApi'

import { Button, Form, Segment, Label, Icon, Input } from 'semantic-ui-react'
import { Bar, Fill } from 'lib/Misc'
import { useCopyToClipboard } from 'hooks/useCopyToClipboard'
import { useForm } from 'react-hook-form'
import { DimmerWithStates } from 'lib/DimmerWithStates'
import { removeUserAccount } from './utils'

const SpokeAccountUsers = ({ category, setValue, labels }) => (
  <div className='user-groups'>
    {labels.map((selectedValue, index) => {
      return (
        <Label basic color={'red'} key={index} size='mini'>
          {selectedValue}
          <Icon
            name='delete'
            onClick={() => {
              const newValues = removeUserAccount(labels, selectedValue)
              setValue(category, newValues)
            }}
          />
        </Label>
      )
    })}
  </div>
)

export const NewSpokeAccount = ({ closeModal, onFinish, defaultValues }) => {
  const [accountOwner, setAccountOwner] = useState('')
  const [accountViewer, setAccountViewer] = useState('')
  const { register, handleSubmit, watch, setValue } = useForm({ defaultValues })

  const { post } = useApi('services/aws/account/spoke')

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
    window.open(
      aws.data?.read_write?.spoke_account_role?.cloudformation_url,
      '_blank'
    )
    closeModal()
  }

  const isIneligible = aws.data?.spoke_account_role?.status === 'ineligible'

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
            <label>Account Name</label>
            <input {...register('account_name', { required: true })} />
          </Form.Field>

          <Form.Field className='custom-checkbox'>
            <input
              className='checkbox-padding'
              type='checkbox'
              {...register('delegate_admin_to_owner')}
            />
            <label className='form-label'>
              Delegate Policy Request Administration to Owner
            </label>
          </Form.Field>

          <Form.Field>
            <label>Account Owners</label>
            <Input
              placeholder='Add owners ...'
              labelPosition='right'
              value={accountOwner}
              onChange={(e) => {
                e.preventDefault()
                setAccountOwner(e.target.value)
              }}
              label={
                <Button
                  type='button'
                  onClick={(e) => {
                    e.preventDefault()
                    if (!accountOwner) return
                    setValue('owners', [...(fields.owners || []), accountOwner])
                    setAccountOwner('')
                  }}
                >
                  Add
                </Button>
              }
            />
            <SpokeAccountUsers
              category='owners'
              labels={fields.owners || []}
              setValue={setValue}
            />
          </Form.Field>

          <Form.Field className='custom-checkbox'>
            <input
              className='checkbox-padding'
              type='checkbox'
              {...register('restrict_viewers_of_account_resources')}
            />

            <label className='form-label'>
              Restrict Viewers of Account Resources
            </label>
          </Form.Field>

          <Form.Field>
            <label>Account Viewers</label>
            <Input
              placeholder='Add viewers ...'
              labelPosition='right'
              value={accountViewer}
              onChange={(e) => {
                e.preventDefault()
                setAccountViewer(e.target.value)
              }}
              label={
                <Button
                  type='button'
                  onClick={(e) => {
                    e.preventDefault()
                    if (!accountViewer) return
                    setValue('viewers', [
                      ...(fields.viewers || []),
                      accountViewer,
                    ])
                    setAccountViewer('')
                  }}
                >
                  Add
                </Button>
              }
            />
            <SpokeAccountUsers
              category='viewers'
              labels={fields.viewers || []}
              setValue={setValue}
            />
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
        <>
          <p style={{ textAlign: 'center' }}>
            You cannot connect your Spoke Accounts before having a Hub Account
            connected.
            <br />
            <strong>
              If you already did, please try to refresh the screen.
            </strong>
          </p>
          <p style={{ textAlign: 'center' }}>
            <Button onClick={() => aws.get()} positive>
              Refresh Screen
            </Button>
          </p>
        </>
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
              value={
                aws.data?.read_write?.spoke_account_role?.cloudformation_url
              }
            />
          </Bar>
        </>
      )}
    </Segment>
  )
}
