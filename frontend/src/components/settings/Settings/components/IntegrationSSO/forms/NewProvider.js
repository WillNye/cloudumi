/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useState } from 'react'
import { useApi } from 'hooks/useApi'

import { useForm } from 'react-hook-form'

import { Form, Button, Segment } from 'semantic-ui-react'
import { DimmerWithStates } from 'lib/DimmerWithStates'
import { Bar, Fill } from 'lib/Misc'
import { ProviderTypeFields } from './ProviderTypeFields'

export const NewProvider = ({ closeModal, onFinish, defaultValues }) => {
  const { register, reset, watch, handleSubmit } = useForm({ defaultValues })

  const { post } = useApi('auth/sso')

  const onSubmit = (data) => {
    let provider = ''
    switch (data?.provider_type) {
      case 'google':
        provider = 'google'
        break
      case 'saml':
        provider = 'saml'
        break
      case 'oidc':
        provider = 'oidc'
        break
      default:
        provider = ''
    }
    post
      .do(data, provider)
      .then(() => {
        closeModal()
        onFinish({ success: true })
      })
      .catch((error) => {
        onFinish({ success: false, message: error.message })
      })
  }

  const [type, setType] = useState()

  const fields = watch()

  delete fields?.user_pool_id

  const fieldsSize = Object.keys(fields)?.length

  const currentFieldsSize = Object.keys(fields)?.filter(
    (key) => fields[key]
  )?.length

  const isReady = fieldsSize !== 0 && currentFieldsSize === fieldsSize

  const isWorking = post?.status === 'working'

  const isSuccess = post?.status === 'done' && !post?.error

  const hasDefault = defaultValues?.provider_type

  useEffect(() => {
    if (hasDefault) setType(defaultValues?.provider_type)
  }, [defaultValues?.provider_type])

  return (
    <Segment basic>
      <DimmerWithStates
        loading={isWorking}
        messageType={isSuccess ? 'success' : 'warning'}
        message={'Something went wrong, try again!'}
      />

      <Form onSubmit={handleSubmit(onSubmit)}>
        <Form.Field>
          <label>Type</label>
          <select
            value={type}
            disabled={hasDefault}
            onChange={({ target }) => {
              setType(target.value)
              reset()
            }}
          >
            <option value=''>Select provider type</option>
            <option value='google'>Google</option>
            <option value='saml'>SAML</option>
            <option value='oidc'>OIDC</option>
          </select>
        </Form.Field>

        <ProviderTypeFields type={type} register={register} />

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
