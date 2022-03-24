import React from 'react'
import { useApi } from 'hooks/useApi'

import { useForm } from 'react-hook-form'

import { Form, Button, Segment } from 'semantic-ui-react'
import { DimmerWithStates } from 'lib/DimmerWithStates'
import { Bar, Fill } from 'lib/Misc'

export const NewUser = ({ closeModal, onFinish }) => {
  const { register, handleSubmit, watch } = useForm()

  const { post } = useApi('auth/cognito/users')

  const onSubmit = (data) => {
    post.do(data).then(() => {
      closeModal()
      onFinish()
    })
  }

  const fields = watch()

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
        message={'Something went wrong, try again!'}
      />

      <Form onSubmit={handleSubmit(onSubmit)}>
        <Form.Field>
          <label>Username</label>
          <input {...register('Username', { required: true })} />
        </Form.Field>

        <Form.Field>
          <label>Password</label>
          <input {...register('temporary_password', { required: true })} />
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
}
