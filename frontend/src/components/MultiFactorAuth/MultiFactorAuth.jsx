import React, { useState, useEffect } from 'react'
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
import './MultiFactorAuth.scss'
import { Link } from 'react-router-dom'

const MultiFactorAuth = () => {
  const [isLoading, setIsLoading] = useState(true)
  const [showManualCode, setShowManualCode] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)

  useEffect(() => {
    setTimeout(() => {
      setIsLoading(false)
    }, 200)
  }, [])

  return (
    <div>
      <NavHeader showMenuItems={false} />
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
            <QRCodeCanvas value='https://reactjs.org/' />
            {showManualCode ? (
              <div className='multi-factor-auth__qrcode_text_code'>
                <p>Input this verification code manually</p>
                <span>
                  <strong>p2uuebe3k6ia75vi</strong>
                </span>
              </div>
            ) : (
              <p
                className='multi-factor-auth__qrcode_text'
                onClick={() => setShowManualCode(true)}
              >
                Trouble Scanning ?
              </p>
            )}
          </div>

          <Header as='h4'>
            Step 2. Enter the six-digit code from your authenticator app
          </Header>

          <Form error>
            <Form.Field className='multi-factor-auth__input'>
              <input
                placeholder='Enter Code here'
                maxlength='6'
                minlength='6'
                required
                disabled={isSuccess}
              />
            </Form.Field>
            {!isSuccess && (
              <>
                <Message
                  error
                  header='Invalid Code'
                  content='The code you entered is incorrect. Please try again.'
                />
                <Button onClick={() => setIsSuccess(true)}>Submit</Button>
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
    </div>
  )
}

export default MultiFactorAuth
