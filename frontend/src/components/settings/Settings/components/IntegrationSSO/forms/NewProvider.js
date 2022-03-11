import React from 'react'
import { useApi } from 'hooks/useApi'

import { useForm } from 'react-hook-form'

import { Form, Button, Segment } from 'semantic-ui-react'
import { DimmerWithStates } from 'lib/DimmerWithStates'
import { Bar, Fill } from 'lib/Misc'

export const NewProvider = ({ closeModal, onFinish }) => {
  const { register, handleSubmit, watch } = useForm()

  const { post } = useApi('integrations/sso/identity-providers')

  const onSubmit = (data) => {
    post.do(data).then(() => {
      closeModal()
      onFinish()
    })
  }

  const watchFields = watch()

  const isReady = !!watchFields.tag_name

  const isWorking = post?.status === 'working'

  const isSuccess = post?.status === 'done' && !post?.error

  const hasError = post?.error && post?.status === 'done'
    
  // {
  //   "idp_type": "oidc",
  //   "idp_settings": {
  //       "client_id": "client_id",
  //       "client_secret": "client_secret",
  //       "attributes_request_method": "attributes_request_method",
  //       "oidc_issuer": "oidc_issuer",
  //       "authorize_scopes": "authorize_scopes",
  //       "token_url": "token_url",
  //       "attributes_url": "attributes_url",
  //       "jwks_uri": "jwks_uri"
  //   }
  // }

  // {
  //   "idp_type": "saml",
  //   "idp_settings": {
  //       "metadata_url": "metadata_url",
  //       "metadata_file": "metadata_file",
  //       "idp_signout": "idp_signout"
  //   }
  // }

  return (
    <Segment basic>
      <DimmerWithStates
        loading={isWorking}
        showMessage={hasError}
        messageType={isSuccess ? 'success' : 'warning'}
        message={'Something went wrong, try again!'}
      />

      <Form onSubmit={handleSubmit(onSubmit)}>

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
