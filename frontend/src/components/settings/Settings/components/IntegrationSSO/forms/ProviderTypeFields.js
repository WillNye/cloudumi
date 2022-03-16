import React from 'react'

import { Form } from 'semantic-ui-react'

export const ProviderTypeFields = ({ type, register }) => {
  const renderGoogleFields = (
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
        value='Google'
        {...register('provider_name', { required: true })}
      />
      <input
        type='hidden'
        value='google'
        {...register('provider_type', { required: true })}
      />
    </>
  )

  const renderSAMLFields = (
    <>
      <Form.Field>
        <label>Metadata URL</label>
        <input {...register('metadata_url', { required: true })} />
      </Form.Field>
      <input
        type='hidden'
        value='SAML'
        {...register('provider_name', { required: true })}
      />
      <input
        type='hidden'
        value='saml'
        {...register('provider_type', { required: true })}
      />
    </>
  )

  const renderOIDCFields = (
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
        value='OIDC'
        {...register('provider_name', { required: true })}
      />
      <input
        type='hidden'
        value='oidc'
        {...register('provider_type', { required: true })}
      />
    </>
  )

  switch (type) {
    case 'google':
      return renderGoogleFields
    case 'saml':
      return renderSAMLFields
    case 'oidc':
      return renderOIDCFields
    default:
      return null
  }
}
