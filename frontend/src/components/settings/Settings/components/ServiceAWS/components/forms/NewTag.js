import React, { useState } from 'react'
import { useApi } from 'hooks/useApi'

import { useForm } from 'react-hook-form'

import { Form, Button, Segment } from 'semantic-ui-react'
import { DimmerWithStates } from 'lib/DimmerWithStates'
import { Bar, Fill } from 'lib/Misc'

export const NewTag = ({ closeModal, onFinish }) => {
  const { register, handleSubmit, watch } = useForm()

  const { post } = useApi(
    'services/aws/role-access/credential-brokering/auth-tags'
  )

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

  const watchFields = watch()

  const isReady = !!watchFields.tag_name

  const isWorking = post?.status === 'working'

  const isSuccess = post?.status === 'done' && !post?.error

  const hasError = post?.error && post?.status === 'done'

  // TODO: Tag keys and values can include any combination of letters, numbers, spaces, and _ . : / = + - @ symbols.

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
          <label>Tag Name</label>
          <input {...register('tag_name', { required: true })} />
        </Form.Field>

        <Form.Field inline>
          <input
            id='check'
            type='checkbox'
            {...register('allow_webconsole_access')}
          />
          <label htmlFor='check'>Allow Web Console Access?</label>
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
