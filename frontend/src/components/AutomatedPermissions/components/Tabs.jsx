import React from 'react'
import { Icon, Segment, Step } from 'semantic-ui-react'
import { TABS_ENUM } from '../constants'

const Tabs = ({ selectedTab }) => {
  return (
    <Segment basic>
      <Step.Group fluid>
        <Step active={selectedTab === TABS_ENUM.STEP_ONE} className={'step1'}>
          <Icon name='handshake' />
          <Step.Content>
            <Step.Title>Discover Permissions</Step.Title>
            <Step.Description>Listen for access denied errors</Step.Description>
          </Step.Content>
        </Step>
        <Step active={selectedTab === TABS_ENUM.STEP_TWO} className={`step2`}>
          <Icon name='search plus' />
          <Step.Content>
            <Step.Title>Generate Permissions</Step.Title>
            <Step.Description>Detected Access Denied Error</Step.Description>
          </Step.Content>
        </Step>
        <Step active={selectedTab === TABS_ENUM.STEP_THREE} className={'step3'}>
          <Icon name='handshake' />
          <Step.Content>
            <Step.Title>Review and Submit</Step.Title>
            <Step.Description>Apply Permissions</Step.Description>
          </Step.Content>
        </Step>
      </Step.Group>
    </Segment>
  )
}

export default Tabs
