import React from 'react'
import { Divider, Form, Header, Radio } from 'semantic-ui-react'

const ConnectionMethod = () => {
  return (
    <div className='on-boarding__instructions'>
      <p>
        In order to securely connect to your AWS Environment, Noq requires
        Cross-Account IAM Roles to be created in at least one of your accounts.
        Please read more about this here.
      </p>

      <p>
        If you’re connecting a single account, we recommend that you use the AWS
        Console or AWS CLI, which will create the roles using CloudFormation and
        inform Noq when it is complete.
      </p>

      <p>
        When the roles are accessible, Noq will begin syncing your account data
        automatically.
      </p>

      <Divider horizontal />

      <Header as='h4'>Select the method you would like to connect Noq:</Header>

      <Form>
        <Form.Field>
          <Radio label='AWS Console' checked />
        </Form.Field>

        <Form.Field>
          <Radio label='AWS CLI (Coming Soon)' disabled />
        </Form.Field>

        <Form.Field>
          <Radio label='Terraform (Coming Soon)' disabled />
        </Form.Field>
      </Form>
    </div>
  )
}

export default ConnectionMethod
