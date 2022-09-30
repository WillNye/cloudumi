import React, { useMemo, useState } from 'react'
import { Divider, Header, Icon, Segment, Step } from 'semantic-ui-react'
import ReviewRequest from './components/ReviewRequest'
import SelectIdentity from './components/SelectIdentity'
import SelectUserGroups from './components/SelectUserGroups'
import { STEPS } from './constants'
import './RequestRoleAccess.scss'

const RequestRoleAccess = () => {
  const [currentStep, setCurrentStep] = useState(STEPS.STEP_ONE)

  const currentSection = useMemo(() => {
    const sections = {
      [STEPS.STEP_ONE]: <SelectIdentity setCurrentStep={setCurrentStep} />,
      [STEPS.STEP_TWO]: <SelectUserGroups setCurrentStep={setCurrentStep} />,
      [STEPS.STEP_THREE]: <ReviewRequest setCurrentStep={setCurrentStep} />,
    }

    return sections[currentStep]
  }, [currentStep])

  return (
    <div>
      <Segment basic>
        <Header as='h2'>Request Access</Header>

        <Divider horizontal />
        <Step.Group fluid>
          <Step
            active={currentStep === STEPS.STEP_ONE}
            onClick={() => {
              if ([STEPS.STEP_TWO, STEPS.STEP_THREE].includes(currentStep)) {
                setCurrentStep(STEPS.STEP_ONE)
              }
            }}
            className={`${
              currentStep !== STEPS.STEP_ONE ? 'complete' : ''
            } step1`}
          >
            <Icon name='handshake' />
            <Step.Content>
              <Step.Title>Select Role</Step.Title>
              <Step.Description>Search and Select Role</Step.Description>
            </Step.Content>
          </Step>
          <Step
            active={currentStep === STEPS.STEP_TWO}
            onClick={() => {
              if ([STEPS.STEP_THREE].includes(currentStep)) {
                setCurrentStep(STEPS.STEP_TWO)
              }
            }}
            className={`${
              currentStep === STEPS.STEP_THREE ? 'complete' : ''
            } step2`}
          >
            <Icon name='search plus' />
            <Step.Content>
              <Step.Title>Select User Groups</Step.Title>
              <Step.Description>Search and Select User Groups</Step.Description>
            </Step.Content>
          </Step>
          <Step active={currentStep === STEPS.STEP_THREE} className={'step3'}>
            <Icon name='handshake' />
            <Step.Content>
              <Step.Title>Review and Submit</Step.Title>
              <Step.Description>Review and Submit Request</Step.Description>
            </Step.Content>
          </Step>
        </Step.Group>
        <Divider horizontal />

        {currentSection}
      </Segment>
    </div>
  )
}

export default RequestRoleAccess
