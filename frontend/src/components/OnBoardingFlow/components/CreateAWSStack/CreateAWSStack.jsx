import React from 'react'
import { Button, Divider, Header, List } from 'semantic-ui-react'
import './CreateAWSStack.scss'

const CreateAWSStack = () => {
  return (
    <div className='connect-stack'>
      <Header as='h3'>1. Login to your chosen AWS Account</Header>
      <Button primary>Login to [AWS Account Name] </Button>

      <Divider horizontal />

      <Header as='h3'>2. ‘CREATE STACK’ in that account</Header>

      <div className='connect-stack__warning-alert__header'>
        <Header as='h4'>What to expect in AWS</Header>
      </div>
      <div className='connect-stack__warning-alert'>
        <List bulleted relaxed>
          <List.Item>
            Select{' '}
            <strong>
              ‘I acknowledge that AWS CloudFormation might create IAM resources
              with custom names’
            </strong>{' '}
            and click <strong>Create Stack.</strong>
          </List.Item>

          <List.Item>
            When all resources have the status <strong>CREATE_COMPLETE</strong>,
            click ‘Next’.
          </List.Item>
        </List>
      </div>
    </div>
  )
}

export default CreateAWSStack
