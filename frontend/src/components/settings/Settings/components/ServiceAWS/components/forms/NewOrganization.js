import React, { useState } from 'react'
import { useApi } from 'hooks/useApi'

import { useForm } from 'react-hook-form'

import { Form, Button, Segment } from 'semantic-ui-react'
import { DimmerWithStates } from 'lib/DimmerWithStates'
import { SelectAccount } from '../../../utils'
import { Bar, Fill } from 'lib/Misc'

export const NewOrganization = ({ closeModal, onFinish }) => {
  const { register, handleSubmit, watch } = useForm()

  const { post } = useApi('services/aws/account/org')

  const [errorMessage, setErrorMessage] = useState(
    'Something went wrong, try again!'
  )

  const onSubmit = (data) => {
    const name = data.account_name.split(' - ')
    data.account_name = name[0]
    data.account_id = name[1]
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

      <Form onSubmit={handleSubmit(onSubmit)}>
        <Form.Field>
          <label>Organization Id</label>
          <input {...register('org_id', { required: true })} />
        </Form.Field>

        <SelectAccount
          label='Spoke Account Name and Id'
          register={{ ...register('account_name', { required: true }) }}
        />

        <Form.Field>
          <label>Owner</label>
          <input {...register('owner', { required: true })} />
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
