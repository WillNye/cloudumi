/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useState } from 'react'

import { Form } from 'semantic-ui-react'

const GoogleFields = ({ register }) => (
  <>
    <Form.Field>
      <label>Client ID</label>
      <input {...register('client_id', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>Client Secret</label>
      <input {...register('client_secret', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>Authorize Scopes</label>
      <input {...register('authorize_scopes', { required: true })} />
    </Form.Field>
    <input
      type='hidden'
      value='google'
      {...register('provider_name', { required: true })}
    />
    <input
      type='hidden'
      value='google'
      {...register('provider_type', { required: true })}
    />
  </>
)

const SAMLFields = ({ register }) => (
  <>
    <Form.Field>
      <label>Metadata URL</label>
      <input {...register('MetadataURL', { required: true })} />
    </Form.Field>
    <input
      type='hidden'
      value='saml'
      {...register('provider_name', { required: true })}
    />
    <input
      type='hidden'
      value='saml'
      {...register('provider_type', { required: true })}
    />
  </>
)

const OIDCFields = ({ register }) => (
  <>
    <Form.Field>
      <label>Client ID</label>
      <input {...register('client_id', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>Client Secret</label>
      <input {...register('client_secret', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>Attributes Request Method</label>
      <input {...register('attributes_request_method', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>OIDC Issuer</label>
      <input {...register('oidc_issuer', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>Authorize Scopes</label>
      <input {...register('authorize_scopes', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>Token URL</label>
      <input {...register('token_url', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>Attributes URL</label>
      <input {...register('attributes_url', { required: true })} />
    </Form.Field>
    <Form.Field>
      <label>JWKS URI</label>
      <input {...register('jwks_uri', { required: true })} />
    </Form.Field>
    <input
      type='hidden'
      value='oidc'
      {...register('provider_name', { required: true })}
    />
    <input
      type='hidden'
      value='oidc'
      {...register('provider_type', { required: true })}
    />
  </>
)

export const ProviderTypeFields = ({ type, register }) => {
  const [render, setRender] = useState(null)

  useEffect(() => {
    switch (type) {
      case 'google':
        return setRender(<GoogleFields register={register} />)
      case 'saml':
        return setRender(<SAMLFields register={register} />)
      case 'oidc':
        return setRender(<OIDCFields register={register} />)
      default:
        return setRender(null)
    }
  }, [type])

  return render
}

// const GoogleFields = {
//   client_id: '[type]',
//   client_secret: '[type]',
//   authorize_scopes: '[type]',
//   provider_name: '[type]',
//   provider_type: '[type]'
// }

// const SAMLFields = {
//   metadata_url: '[type]',
//   provider_name: '[type]',
//   provider_type: '[type]'
// }

// const OIDCFields = {
//   client_id: '[type]',
//   client_secret: '[type]',
//   attributes_request_method: '[type]',
//   oidc_issuer: '[type]',
//   authorize_scopes: '[type]',
//   token_url: '[type]',
//   attributes_url: '[type]',
//   jwks_uri: '[type]',
//   provider_name: '[type]',
//   provider_type: '[type]'
// }
