import React, { useCallback, useEffect } from 'react'
import { Divider, Header, Icon } from 'semantic-ui-react'
import { TIME_PER_INTERVAL } from 'components/OnBoardingFlow/constants'
import { useAuth } from 'auth/AuthProviderDefault'
import './CheckAccountConnection.scss'

const CheckAccountConnection = ({
  setIsConnected,
  isHubAccount,
  accountName,
}) => {
  const { sendRequestCommon } = useAuth()

  const getAccountDetails = useCallback(async () => {
    const accountUrlPath = isHubAccount ? 'hub' : 'spoke'
    const resJson = await sendRequestCommon(
      null,
      `/api/v3/services/aws/account/${accountUrlPath}`,
      'get'
    )
    if (resJson && resJson.count) {
      if (isHubAccount) {
        setIsConnected(true)
      } else {
        resJson?.data.forEach((acc) => {
          if (acc.account_name === accountName) {
            setIsConnected(true)
          }
        })
      }
    }
  }, [isHubAccount, accountName]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const interval = setInterval(async () => {
      await getAccountDetails()
    }, TIME_PER_INTERVAL)

    return () => {
      clearInterval(interval)
    }
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
