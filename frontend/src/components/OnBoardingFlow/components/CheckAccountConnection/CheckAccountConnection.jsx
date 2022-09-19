import React, { useEffect } from 'react'
import { Divider, Header, Icon } from 'semantic-ui-react'
import './CheckAccountConnection.scss'

const CheckAccountConnection = ({ setIsConnected }) => {
  useEffect(() => {
    setTimeout(() => {
      setIsConnected(true)
    }, 10000)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className='connecting-account'>
      <div>
        <Divider horizontal />
        <Divider horizontal />
        <Header as='h3'>
          <Icon loading name='sync' size='small' />
          <Header.Content>
            Onboarding account
            <Header.Subheader>
              Waiting for CloudFormation response.
            </Header.Subheader>
          </Header.Content>
        </Header>
        <Divider horizontal />
        <Divider horizontal />
        <Header as='h3'>
          <Icon name='ban' />
          <Header.Content>
            Caching resources
            <Header.Subheader>Not started</Header.Subheader>
          </Header.Content>
        </Header>
      </div>
    </div>
  )
}

export default CheckAccountConnection
