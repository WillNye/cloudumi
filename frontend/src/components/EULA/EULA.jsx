import { useAuth } from 'auth/AuthProviderDefault'
import React, { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Button,
  Checkbox,
  Divider,
  Header,
  Message,
  Popup,
  Segment,
} from 'semantic-ui-react'
import NavHeader from '../Header'
import './eula.scss'

const SCROLL_HEIGHT_OFFSET = 5

const EULA = () => {
  const { sendRequestCommon } = useAuth()

  const ref = useRef()

  const [isLoading, setIsLoading] = useState(true)
  const [agreementDocument, setAgreementDocument] = useState('')
  const [hasViewedAgreement, setHasViewedAgreement] = useState(false)
  const [acceptAgreement, setAcceptAgreemnet] = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const [fetchError, setFetchError] = useState(null)

  useEffect(function onMount() {
    setIsLoading(true)
    sendRequestCommon(null, '/api/v3/legal/agreements/eula', 'get')
      .then((res) => {
        if (res?.data?.eula) {
          setAgreementDocument(res.data.eula)
        } else {
          setFetchError(JSON.stringify(res))
        }
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleOnSubmit = () => {
    setIsLoading(true)
    sendRequestCommon(null, 'api/v3/tenant/details/eula', 'post').then(
      (res) => {
        if ([400, 200].includes(res?.status_code)) {
          window.location.href = '/'
        } else {
          setSubmitError(JSON.stringify(res))
          setIsLoading(false)
        }
      }
    )
  }

  const onScroll = () => {
    if (ref.current) {
      const { scrollTop, scrollHeight, clientHeight } = ref.current
      const height = scrollTop + clientHeight
      if (height + SCROLL_HEIGHT_OFFSET >= scrollHeight) {
        setHasViewedAgreement(true)
      }
    }
  }

  return (
    <>
      <NavHeader showMenuItems={false} />

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
              as='h1'
              color='grey'
              style={{
                fontSize: '36px',
              }}
              textAlign='center'
            >
              An error occured
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
          <div className='eula'>
            <Header as='h3'>Terms of Service</Header>
            <Segment>
              <textarea
                onScroll={onScroll}
                ref={ref}
                className='eula__documnet'
                readOnly
                value={agreementDocument}
              ></textarea>
            </Segment>

            <Divider horizontal />

            {submitError && (
              <Message error header='Error' content={submitError} />
            )}

            <div className='eula__actions'>
              <p>
                By clicking below, you agree to the Noq Terms and Conditons of
                Service and Privacy Policy.
              </p>
            </div>

            <Divider horizontal />

            <div className='eula__actions'>
              <Popup
                content='Read the EULA to continue (scroll to the bottom)'
                disabled={hasViewedAgreement}
                trigger={
                  <Checkbox
                    label='Accept'
                    onChange={(_event, data) =>
                      setAcceptAgreemnet(data.checked)
                    }
                    checked={acceptAgreement}
                    disabled={!hasViewedAgreement}
                  />
                }
              />
            </div>

            <Divider horizontal />

            <div className='eula__actions'>
              <Button
                className='eula__buttton'
                primary
                fluid
                disabled={!acceptAgreement}
                onClick={handleOnSubmit}
              >
                Continue
              </Button>
            </div>
          </div>
        </Segment>
      )}
    </>
  )
}

export default EULA
