import React, { useCallback, useMemo, useState } from 'react'
import { useApi } from 'hooks/useApi'
import { useForm } from 'react-hook-form'
import { Form, Button, Segment } from 'semantic-ui-react'
import { DimmerWithStates } from 'lib/DimmerWithStates'
import { SelectAccount } from '../../../utils'
import { Bar, Fill } from 'lib/Misc'

export const NewOrganization = ({ closeModal, onFinish, defaultValues }) => {
  const { register, handleSubmit, watch, setValue } = useForm({ defaultValues })

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

  const onOptionsLoad = useCallback(() => {
    if (defaultValues.account_name) {
      setValue('account_name', defaultValues.account_name)
      setValue('ord_id', defaultValues.org_id)
    }
  }, [defaultValues, setValue])

  const fields = watch()

  const isReady = useMemo(() => {
    return Boolean(fields.org_id && fields.account_name && fields.owner)
  }, [fields])

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
          onOptionsLoad={onOptionsLoad}
        />

        <Form.Field>
          <label>Owner</label>
          <input {...register('owner', { required: true })} />
        </Form.Field>

        <Form.Field className='custom-checkbox'>
          <input
            className='checkbox-padding'
            type='checkbox'
            {...register('automatically_onboard_accounts', { required: false })}
          />
          <label className='form-label'>Automatically Onboard Accounts</label>
        </Form.Field>

        <Form.Field className='custom-checkbox'>
          <input
            className='checkbox-padding'
            type='checkbox'
            {...register('sync_account_names', { required: false })}
          />
          <label className='form-label'>Sync Account Names</label>
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
