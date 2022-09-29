import React, { useState, useEffect } from 'react'
import { Button, Divider, Header, List, Message } from 'semantic-ui-react'
import { useAuth } from 'auth/AuthProviderDefault'
import { getCloudFormationUrl } from 'components/OnBoardingFlow/utils'
import { useCopyToClipboard } from 'hooks/useCopyToClipboard'
import './CreateAWSStack.scss'

const CreateAWSStack = ({
  accountName,
  setIsLoading,
  isHubAccount,
  selectedMode,
}) => {
  const [generateLinkError, setGenerateLinkError] = useState(null)
  const [cloudFormationUrl, setCloudFormationUrl] = useState('')

  const { sendRequestCommon } = useAuth()

  const { CopyButton } = useCopyToClipboard()

  useEffect(() => {
    setGenerateLinkError(null)
    generateAWSLoginLink()
    return () => {
      setGenerateLinkError(null)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const generateAWSLoginLink = async () => {
    setIsLoading(true)
    const res = await sendRequestCommon(
      null,
      `/api/v3/integrations/aws?account-name=${accountName}`,
      'get'
    )

    if (res?.status_code === 200) {
      const url = getCloudFormationUrl(res.data, selectedMode, isHubAccount)
      setCloudFormationUrl(url)
      setIsLoading(false)
      return
    }

    if (res?.status_code === 400) {
      setGenerateLinkError(res?.message)
      setIsLoading(false)
      return
    }
  }

  const handleClick = () => {
    window.open(cloudFormationUrl, '_blank')
  }

  return (
    <div className='connect-stack'>
      <Divider horizontal />

      <Header as='h4'>1. Login to your chosen AWS Account</Header>

      <div>
        <Button primary onClick={handleClick}>
          Login to {accountName}
        </Button>
        <CopyButton value={cloudFormationUrl} />
      </div>

      {generateLinkError && (
        <Message negative>
          <Message.Header>Unable to generate AWs login link</Message.Header>
          <p>{generateLinkError}</p>
        </Message>
      )}

      <Divider horizontal />
      <Header as='h4'>2. ‘CREATE STACK’ in that account</Header>

      <div className='connect-stack__warning-alert__header'>
        <Header as='h5'>What to expect in AWS</Header>
      </div>
      <div className='connect-stack__warning-alert'>
        <List bulleted relaxed>
          <List.Item>
            Select{' '}
            <strong>
              <i>
                ‘I acknowledge that AWS CloudFormation might create IAM
                resources with custom names’
              </i>
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
