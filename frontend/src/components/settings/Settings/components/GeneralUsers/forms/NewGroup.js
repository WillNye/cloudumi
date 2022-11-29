import React, { useState, useMemo } from 'react'
import { useApi } from 'hooks/useApi'

import { useForm } from 'react-hook-form'

import { Form, Button, Segment, Message } from 'semantic-ui-react'
import { DimmerWithStates } from 'lib/DimmerWithStates'
import { Bar, Fill } from 'lib/Misc'

export const NewGroup = ({ closeModal, onFinish, defaultValues }) => {
  const { register, handleSubmit, watch } = useForm({ defaultValues })

  const { post } = useApi('auth/cognito/groups')

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

  const groupNameError = useMemo(() => {
    const value = fields.GroupName || ''
    if (value && !/^[a-zA-Z_0-9+=,.@-_]+$/.test(value)) {
      return 'Group name should only contain alphanumeric characters and +=,.@_-'
    }
    return null
  }, [fields])

  const fieldsSize = Object.keys(fields)?.length

  const currentFieldsSize = Object.keys(fields)?.filter(
    (key) => fields[key]
  )?.length

  const isReady = fieldsSize !== 0 && currentFieldsSize === fieldsSize

  const isWorking = post?.status === 'working'

  const isSuccess = post?.status === 'done' && !post?.error

  const hasError = post?.error && post?.status === 'done'

  return (
    <Segment basic>
      <DimmerWithStates
        loading={isWorking}
        showMessage={hasError}
        messageType={isSuccess ? 'success' : 'warning'}
        message={errorMessage}
      />

      <Form onSubmit={handleSubmit(onSubmit)} error>
        <Form.Field error={Boolean(groupNameError)}>
          <label>Group Name</label>
          <input {...register('GroupName', { required: true })} />
          {groupNameError && <Message error content={groupNameError} />}
        </Form.Field>

        <Form.Field>
          <label>Description</label>
          <input {...register('Description', { required: true })} />
        </Form.Field>

        <Bar>
          <Fill />
          <Button
            type='submit'
            disabled={!isReady || Boolean(groupNameError)}
            positive
          >
            Submit
          </Button>
        </Bar>
      </Form>
    </Segment>
  )
}
