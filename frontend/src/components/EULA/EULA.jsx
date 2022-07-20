import { useAuth } from 'auth/AuthProviderDefault'
import React, { useEffect, useRef, useState } from 'react'
import { Button, Checkbox, Divider, Header, Segment } from 'semantic-ui-react'
import NavHeader from '../Header'
import './eula.css'

const EULA = ({ history }) => {
  const { sendRequestCommon } = useAuth()

  const ref = useRef()

  const [isLoading, setIsLoading] = useState(true)
  const [agreementDocument, setAgreementDocument] = useState('')
  const [hasViewedAgreement, setHasViewedAgreement] = useState(false)
  const [acceptAgreement, setAcceptAgreemnet] = useState(false)

  useEffect(function onMount() {
    setIsLoading(true)
    sendRequestCommon(null, '/api/v3/legal/agreements/eula', 'get')
      .then((res) => {
        setAgreementDocument(res?.data?.eula)
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [])

  const handleOnSubmit = () => {
    setIsLoading(true)
    sendRequestCommon(null, 'api/v3/tenant/details/eula', 'post')
      .then(() => {
        history.push('/')
      })
      .finally(() => {
        setIsLoading(false)
      })
  }

  const onScroll = () => {
    if (ref.current) {
      const { scrollTop, scrollHeight, clientHeight } = ref.current
      if (scrollTop + clientHeight === scrollHeight) {
        setHasViewedAgreement(true)
      }
    }
  }

  return (
    <>
      <NavHeader showMenuItems={false} />
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

          <div className='eula__actions'>
            <p>
              By clicking below, you agree to the Noq Terms and Conditons of
              Service and Privacy Policy.
            </p>
          </div>

          <Divider horizontal />

          <div className='eula__actions'>
            <Checkbox
              label='Accept'
              onChange={(_event, data) => setAcceptAgreemnet(data.checked)}
              checked={acceptAgreement}
              disabled={!hasViewedAgreement}
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
    </>
  )
}

export default EULA
