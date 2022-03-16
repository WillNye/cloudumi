import React from 'react'
import { useApi } from 'hooks/useApi'

import { useForm } from 'react-hook-form'

import { Form, Button, Segment } from 'semantic-ui-react'
import { DimmerWithStates } from 'lib/DimmerWithStates'
import { Bar, Fill } from 'lib/Misc'
import { useGeoIP } from 'hooks/useGeoIP'

export const NewCIDR = ({ closeModal, onFinish }) => {
  const { register, handleSubmit, watch } = useForm()

  const { post } = useApi('services/aws/ip-access')

  // const { data, status } = useGeoIP()

  // console.log(data, status)

  const onSubmit = (data) => {
    post.do(data).then(() => {
      closeModal()
      onFinish()
    })
  }

  const watchFields = watch()

  const isReady = !!watchFields.cidr

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
          <label>CIDR</label>
          <input {...register('cidr', { required: true })} />
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
