import { useState } from 'react'
import { Divider, Header, Icon, Segment, Step } from 'semantic-ui-react'
import RequestForm from './components/RequestForm'
import RequestReview from './components/RequestReview'
import { ROLE_CREATION_STEPS } from './constants'
import './RequestRoleCreation.scss'

const RequestRoleCreation = () => {
  const [currentStep, setCurrentStep] = useState(ROLE_CREATION_STEPS.STEP_ONE)
  const [formData, setFormData] = useState({})

  return (
    <section>
      <Header as='h2'>Request Role Creation</Header>
      <div className='role-creation'>
        <Divider horizontal />

        <Step.Group fluid>
          <Step
            active={currentStep === ROLE_CREATION_STEPS.STEP_ONE}
            onClick={() => {
              if ([ROLE_CREATION_STEPS.STEP_TWO].includes(currentStep)) {
                setCurrentStep(ROLE_CREATION_STEPS.STEP_ONE)
              }
            }}
            className={`${
              currentStep !== ROLE_CREATION_STEPS.STEP_ONE ? 'complete' : ''
            } step1`}
          >
            <Icon name='handshake' />
            <Step.Content>
              <Step.Title>Enter Role Details</Step.Title>
              <Step.Description>Select account to add role</Step.Description>
            </Step.Content>
          </Step>
          <Step
            active={currentStep === ROLE_CREATION_STEPS.STEP_TWO}
            className={`${
              currentStep === ROLE_CREATION_STEPS.STEP_THREE ? 'complete' : ''
            } step2`}
          >
            <Icon name='search plus' />
            <Step.Content>
              <Step.Title>Review and Submit</Step.Title>
              <Step.Description>Review and Submit</Step.Description>
            </Step.Content>
          </Step>
        </Step.Group>
        <Divider horizontal />

        <Segment basic>
          {currentStep === ROLE_CREATION_STEPS.STEP_ONE ? (
            <RequestForm
              formData={formData}
              setFormData={setFormData}
              setCurrentStep={setCurrentStep}
            />
          ) : (
            <RequestReview
              formData={formData}
              setCurrentStep={setCurrentStep}
            />
          )}
        </Segment>
      </div>
    </section>
  )
}

export default RequestRoleCreation
