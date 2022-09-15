import React, { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { QRCodeCanvas } from 'qrcode.react'
import {
  Button,
  Divider,
  Form,
  Header,
  Message,
  Segment,
} from 'semantic-ui-react'
import NavHeader from 'components/Header'
import { useAuth } from 'auth/AuthProviderDefault'
import './MultiFactorAuth.scss'

const MultiFactorAuth = () => {
  const [isLoading, setIsLoading] = useState(false)
  const [showManualCode, setShowManualCode] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)
  const [fetchError, setFetchError] = useState(null)
  const [submitError, setSubmitError] = useState(null)
  const [mfaData, setMfaData] = useState({})
  const [userCode, setUserCode] = useState('')

  const { sendRequestCommon } = useAuth()

  useEffect(() => {
    setIsLoading(true)
    sendRequestCommon(null, '/api/v3/auth/cognito/setup-mfa', 'get')
      .then((res) => {
        if (res?.TotpUri) {
          setMfaData(res)
        } else {
          setFetchError(JSON.stringify(res))
        }
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleOnSubmit = useCallback(() => {
    if (!mfaData) return

    setIsLoading(true)
    sendRequestCommon(
      {
        user_code: userCode,
        access_token: mfaData.AccessToken,
      },
      '/api/v3/auth/cognito/setup-mfa',
      'post'
    )
      .then((res) => {
        if (res?.status === 'success') {
          setIsSuccess(true)
        } else {
          setSubmitError(JSON.stringify(res))
        }
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [userCode, mfaData, sendRequestCommon])

  return (
    <div>
      <NavHeader showMenuItems={false} />
      <>
        {fetchError ? (
          <Segment
            basic
            style={{
              height: '100vh',
            }}
            className='eula__actions'
            textAlign='center'
          >
            <div>
              <Header
                as='h2'
                color='grey'
                style={{
                  fontSize: '20px',
                }}
                textAlign='center'
              >
                An error occured
                <Divider horizontal />
                <Header.Subheader>
                  We are already informed, please try again later
                </Header.Subheader>
              </Header>
              <br />
              <Link to='/'>
                <Button content='Return to Home' primary size='large' />
              </Link>
            </div>
          </Segment>
        ) : (
          <Segment basic loading={isLoading}>
            <div className='multi-factor-auth'>
              <Header as='h2'>Multi-factor Authentication</Header>
              <p>
                The security of your account is important to us, this is why we
                require you to set-up multi-factor authentication.
              </p>

              <Header as='h4'>Step 1. Scan QR Code</Header>
              <p>
                After downloading an authentication app such as Google
                Authenticator, Duo Mobile, or Authy, open the app and scan the
                following QR code.
              </p>
              <div className='multi-factor-auth__qrcode'>
                <Divider horizontal />
                <QRCodeCanvas value={mfaData.TotpUri} />
                {showManualCode ? (
                  <div className='multi-factor-auth__qrcode_text_code'>
                    <p>Input this verification code manually</p>
                    <span>
                      <strong>{mfaData.SecretCode}</strong>
                    </span>
                  </div>
                ) : (
                  <p
                    className='multi-factor-auth__qrcode_text'
                    onClick={() => setShowManualCode(true)}
                  >
                    Trouble Scanning?
                  </p>
                )}
              </div>

              <Header as='h4'>
                Step 2. Enter the six-digit code from your authenticator app
              </Header>

              <Form error={!!submitError} onSubmit={handleOnSubmit}>
                <Form.Input
                  className='multi-factor-auth__input'
                  placeholder='Enter Code here'
                  maxLength='6'
                  minLength='6'
                  required
                  value={userCode}
                  onChange={(_e, { value }) => setUserCode(value)}
                  disabled={isSuccess}
                />
                {!isSuccess && (
                  <>
                    <Message
                      error
                      header='Invalid Code'
                      content={submitError}
                    />
                    <Button type='submit'>Submit</Button>
                  </>
                )}
              </Form>

              {isSuccess && (
                <div>
                  <Divider horizontal />
                  <Message
                    success
                    header='MFA has been successfully set'
                    content='Please click the below to continue with your setup'
                  />
                  <Divider horizontal />
                  <Link to='/'>
                    <Button primary>Continue</Button>
                  </Link>
                </div>
              )}
            </div>
          </Segment>
        )}
      </>
    </div>
  )
}

export default MultiFactorAuth
