import React from 'react'
import { useApi } from 'hooks/useApi'

import { useForm } from 'react-hook-form'

import { Form, Button, Segment } from 'semantic-ui-react'
import { DimmerWithStates } from 'lib/DimmerWithStates'
import { Bar, Fill } from 'lib/Misc'
import { ProviderTypeFields } from './ProviderTypeFields'

export const NewProvider = ({ closeModal, onFinish }) => {
  const { register, handleSubmit, watch } = useForm()

  const { post } = useApi('auth/sso')

  const onSubmit = (data) => {
    console.log(data)
    // post.do(data).then(() => {
    //   closeModal()
    //   onFinish()
    // })
  }

  const watchFields = watch()

  const isReady = !!watchFields.tag_name || true

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
          <label>Type</label>
          <select {...register('idp_type', { required: true })}>
            <option value=''>Select one account</option>
            <option value='google'>Google</option>
            <option value='saml'>SAML</option>
            <option value='oidc'>OIDC</option>
          </select>
        </Form.Field>

        <ProviderTypeFields type={watchFields?.idp_type} register={register} />

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
