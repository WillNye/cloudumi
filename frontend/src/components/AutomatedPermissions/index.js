import React, { useEffect, useState } from 'react'
import { Segment, Loader, Divider, Header, Step, Icon } from 'semantic-ui-react'
import { useAuth } from '../../auth/AuthProviderDefault'
import PolicyRequestItem from './PolicyRequestItem'
import { TIME_PER_INTERVAL } from './constants'
import { getAllPolicyRequests } from './utils'
import './index.css'

const AutomaticPermissionsList = () => {
  const { sendRequestCommon } = useAuth()
  const [policyRequests, setPolicyRequests] = useState([])

  const getAutomaticPermissionsRequests = async () => {
    const resJson = await getAllPolicyRequests(sendRequestCommon)

    if (resJson && resJson.count) {
      const requests = resJson.data
      setPolicyRequests(requests)
    } else {
      setPolicyRequests([])
    }
  }

  useEffect(() => {
    const interval = setInterval(async () => {
      await getAutomaticPermissionsRequests()
    }, TIME_PER_INTERVAL)

    // get requests onMount
    getAutomaticPermissionsRequests().then()

    return () => {
      clearInterval(interval)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <Step.Group fluid>
        <Step>
          <Icon name='assistive listening systems' color='blue' />
          <Step.Content>
            <Step.Title>Discover Permissions</Step.Title>
            <Step.Description>Listen for access denied errors</Step.Description>
          </Step.Content>
        </Step>
      </Step.Group>
      <Segment size='massive' basic>
        <Divider horizontal />
        <Loader active size='massive'>
          <p className='loader-text'>
            <b> Listening for Access Denied errors</b>
          </p>
        </Loader>
        <Divider horizontal />
      </Segment>
      <div className='description-text'>
        <p>
          Configure Noq to run in proxy mode to automatically detect, generate,
          and request policies to resolve Access Denied errors.
        </p>
        <p>
          If the requested permissions are within your organization's risk
          tolerance, they will be automatically approved and applied to the
          role, and Noq will transparently retry the request without ever return
          an access denied error.
        </p>
      </div>
      <Divider />

      <Header as='h3' block textAlign='center'>
        Generated Policy Requests
      </Header>

      {policyRequests.length ? (
        policyRequests.map((policyRequest, index) => (
          <PolicyRequestItem
            key={policyRequest.policy.Statement[0].Action[0]}
            policyRequest={policyRequest}
            getAutomaticPermissionsRequests={getAutomaticPermissionsRequests}
            sendRequestCommon={sendRequestCommon}
          />
        ))
      ) : (
        <Segment placeholder>
          <Header align='center' sub>
            No Permissions detected yet
          </Header>
        </Segment>
      )}
    </>
  )
}

export default AutomaticPermissionsList
