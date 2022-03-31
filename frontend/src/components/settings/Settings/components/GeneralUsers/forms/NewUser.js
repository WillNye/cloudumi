import React from 'react'
import { useApi } from 'hooks/useApi'

import { useForm } from 'react-hook-form'

import { Form, Button, Segment } from 'semantic-ui-react'
import { DimmerWithStates } from 'lib/DimmerWithStates'
import { Bar, Fill } from 'lib/Misc'
import { Password, SelectGroup } from '../../utils'

export const NewUser = ({ closeModal, onFinish, defaultValues }) => {
  const { register, handleSubmit, watch } = useForm({ defaultValues })

  const { post } = useApi('auth/cognito/users')

  const onSubmit = (data) => {
    post.do(data).then(() => {
      closeModal()
      onFinish()
    })
  }

  const fields = watch()

  const currentFieldsSize = Object.keys(fields)?.filter(
    (key) => fields[key]
  )?.length

  const isReady = currentFieldsSize >= 1

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

        <SelectGroup
          label='Groups'
          defaultValues={defaultValues?.Groups}
          register={{ ...register('Groups') }}
        />

        {defaultValues ? (
          <Password defaultValue={defaultValues?.TemporaryPassword} />
        ) : (
          <p>
            <strong>
              A temporary password will be generated automatically
            </strong>
          </p>
        )}

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