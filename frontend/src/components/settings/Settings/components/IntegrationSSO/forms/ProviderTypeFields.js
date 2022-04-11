/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useState } from 'react'

import { Form } from 'semantic-ui-react'

const GoogleFields = ({ register }) => (
  <>
    <Form.Field>
      <label>Client ID</label>
      <input type='text' {...register('client_id', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>Client Secret</label>
      <input type='text' {...register('client_secret', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>Authorize Scopes</label>
      <input
        type='text'
        {...register('authorize_scopes', { required: true })}
      />
    </Form.Field>
    <input
      type='hidden'
      value='Google'
      {...register('provider_name', { required: true })}
    />
    <input
      type='hidden'
      value='Google'
      {...register('provider_type', { required: true })}
    />
  </>
)

const SAMLFields = ({ register }) => (
  <>
    <Form.Field>
      <label>Metadata URL</label>
      <input type='text' {...register('MetadataURL', { required: true })} />
    </Form.Field>
    <input
      type='hidden'
      value='saml'
      {...register('provider_name', { required: true })}
    />
    <input
      type='hidden'
      value='SAML'
      {...register('provider_type', { required: true })}
    />
  </>
)

const OIDCFields = ({ register }) => (
  <>
    <Form.Field>
      <label>Client ID</label>
      <input type='text' {...register('client_id', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>Client Secret</label>
      <input type='text' {...register('client_secret', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>Attributes Request Method</label>
      <input
        type='text'
        {...register('attributes_request_method', { required: true })}
      />
    </Form.Field>
    <Form.Field>
      <label>OIDC Issuer</label>
      <input type='text' {...register('oidc_issuer', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>Authorize Scopes</label>
      <input
        type='text'
        {...register('authorize_scopes', { required: true })}
      />
    </Form.Field>
    <Form.Field>
      <label>Token URL</label>
      <input type='text' {...register('token_url', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>Attributes URL</label>
      <input type='text' {...register('attributes_url', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>JWKS URI</label>
      <input type='text' {...register('jwks_uri', { required: true })} />
    </Form.Field>
    <input
      type='hidden'
      value='oidc'
      {...register('provider_name', { required: true })}
    />
    <input
      type='hidden'
      value='OIDC'
      {...register('provider_type', { required: true })}
    />
  </>
)

export const ProviderTypeFields = ({ type, register }) => {
  const [render, setRender] = useState(null)

  useEffect(() => {
    switch (type) {
      case 'Google':
        return setRender(<GoogleFields register={register} />)
      case 'SAML':
        return setRender(<SAMLFields register={register} />)
      case 'OIDC':
        return setRender(<OIDCFields register={register} />)
      default:
        return setRender(null)
    }
  }, [type])

  return render
}
