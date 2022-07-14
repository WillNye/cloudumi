import React, { useRef, useState } from 'react'
import { Button, Checkbox, Divider, Header, Segment } from 'semantic-ui-react'
import NavHeader from '../Header'
import './eula.css'

const EULA = () => {
  const ref = useRef()

  const [hasViewedAgreement, setHasViewedAgreement] = useState(false)
  const [acceptAgreement, setAcceptAgreemnet] = useState(false)

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
      <div className='eula'>
        <Header as='h3'>Terms of Service</Header>
        <Segment>
          <div onScroll={onScroll} ref={ref} className='eula__documnet'>
            <p>
              End-User License Agreement (EULA) of Noq This End-User License
              Agreement ("EULA") is a legal agreement between you and Noq. Our
              EULA was created by EULA Template for Noq.
            </p>
            <p>
              This EULA agreement governs your acquisition and use of our Noq
              software ("Software") directly from Noq or indirectly through a
              Noq authorized reseller or distributor (a "Reseller").
            </p>
            <p>
              Please read this EULA agreement carefully before completing the
              installation process and using the Noq software. It provides a
              license to use the Noq software and contains warranty information
              and liability disclaimers.
            </p>
            <p>
              If you register for a free trial of the Noq software, this EULA
              agreement will also govern that trial. By clicking "accept" or
              installing and/or using the Noq software, you are confirming your
              acceptance of the Software and agreeing to become bound by the
              terms of this EULA agreement.
            </p>
            <p>
              If you are entering into this EULA agreement on behalf of a
              company or other legal entity, you represent that you have the
              authority to bind such entity and its affiliates to these terms
              and conditions. If you do not have such authority or if you do not
              agree with the terms and conditions of this EULA agreement, do not
              install or use the Software, and you must not accept this EULA
              agreement.
            </p>
            <p>
              This EULA agreement shall apply only to the Software supplied by
              Noq herewith regardless of whether other software is referred to
              or described herein. The terms also apply to any Noq updates,
              supplements, Internet-based services, and support services for the
              Software, unless other terms accompany those items on delivery. If
              so, those terms apply.
            </p>
            <h3>License Grant</h3>
            <p>
              Noq hereby grants you a personal, non-transferable, non-exclusive
              licence to use the Noq software on your devices in accordance with
              the terms of this EULA agreement.
            </p>
            <p>
              You are permitted to load the Noq software (for example a PC,
              laptop, mobile or tablet) under your control. You are responsible
              for ensuring your device meets the minimum requirements of the Noq
              software.
            </p>
            <h3>You are not permitted to:</h3>
            <p>
              Edit, alter, modify, adapt, translate or otherwise change the
              whole or any part of the Software nor permit the whole or any part
              of the Software to be combined with or become incorporated in any
              other software, nor decompile, disassemble or reverse engineer the
              Software or attempt to do any such things Reproduce, copy,
              distribute, resell or otherwise use the Software for any
              commercial purpose Allow any third party to use the Software on
              behalf of or for the benefit of any third party Use the Software
              in any way which breaches any applicable local, national or
              international law use the Software for any purpose that Noq
              considers is a breach of this EULA agreement Intellectual Property
              and Ownership
            </p>
            <p>
              Noq shall at all times retain ownership of the Software as
              originally downloaded by you and all subsequent downloads of the
              Software by you. The Software (and the copyright, and other
              intellectual property rights of whatever nature in the Software,
              including any modifications made thereto) are and shall remain the
              property of Noq.
            </p>
            <p>
              Noq reserves the right to grant licences to use the Software to
              third parties.
            </p>
            <h3>Termination</h3>
            <p>
              This EULA agreement is effective from the date you first use the
              Software and shall continue until terminated. You may terminate it
              at any time upon written notice to Noq.
            </p>
            <p>
              It will also terminate immediately if you fail to comply with any
              term of this EULA agreement. Upon such termination, the licenses
              granted by this EULA agreement will immediately terminate and you
              agree to stop all access and use of the Software. The provisions
              that by their nature continue and survive will survive any
              termination of this EULA agreement.
            </p>
            <h3>Governing Law</h3>
            <p>
              This EULA agreement, and any dispute arising out of or in
              connection with this EULA agreement, shall be governed by and
              construed in accordance with the laws of us.
            </p>
          </div>
        </Segment>

        <Divider horizontal />
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
          >
            Continue
          </Button>
        </div>
      </div>
    </>
  )
}

export default EULA
