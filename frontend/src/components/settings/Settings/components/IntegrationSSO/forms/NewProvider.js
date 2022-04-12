/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useState } from 'react'
import { useApi } from 'hooks/useApi'

import { useForm } from 'react-hook-form'

import { Form, Button, Segment } from 'semantic-ui-react'
import { DimmerWithStates } from 'lib/DimmerWithStates'
import { Bar, Fill } from 'lib/Misc'
import { ProviderTypeFields } from './ProviderTypeFields'

export const NewProvider = ({
  closeModal,
  onFinish,
  defaultValues,
  existentProviders,
}) => {
  const { register, reset, watch, handleSubmit } = useForm({ defaultValues })

  const { post } = useApi('auth/sso')

  const [errorMessage, setErrorMessage] = useState(
    'Something went wrong, try again!'
  )

  const onSubmit = (data) => {
    let provider = ''
    switch (data?.provider_type) {
      case 'Google':
        provider = 'Google'
        break
      case 'SAML':
        provider = 'SAML'
        break
      case 'OIDC':
        provider = 'OIDC'
        break
      default:
        provider = ''
    }
    post
      .do(data, provider.toLowerCase())
      .then(() => {
        closeModal()
        onFinish({ success: true })
      })
      .catch(({ errorsMap, message }) => {
        console.log(errorsMap, message)
        setErrorMessage(errorsMap || message)
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

  const hasError = post?.error && post?.status === 'done'

  useEffect(() => {
    if (hasDefault) setType(defaultValues?.provider_type)
  }, [defaultValues?.provider_type])

  return (
    <Segment basic>
      <DimmerWithStates
        loading={isWorking}
        showMessage={hasError}
        messageType={isSuccess ? 'success' : 'warning'}
        message={errorMessage}
      />

      <Form onSubmit={handleSubmit(onSubmit)}>
        {!hasDefault ? (
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
              {!existentProviders?.google && (
                <option value='Google'>Google</option>
              )}
              {!existentProviders?.saml && <option value='SAML'>SAML</option>}
              {!existentProviders?.oidc && <option value='OIDC'>OIDC</option>}
            </select>
          </Form.Field>
        ) : (
          <h3>
            <small>Editing provider: </small>
            {defaultValues?.provider_type}
          </h3>
        )}

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
