import React from 'react'
import './Stepper.scss'

export function Step(props) {
  return (
    <div className={'stepBlock' + (props.selected ? ' selected' : '')}>
      <div
        className='circleWrapper'
        onClick={() => props.updateStep(props.index + 1)}
      >
        <div className='circle'>{props.index + 1}</div>
      </div>
      <span>{props.label}</span>
    </div>
  )
}

const Stepper = (props) => {
  const { stepperDetails } = props
  const labelArray = ['Step 1', 'Step 2', 'Step 3', 'Step 4', 'Step 5']
  return (
    <div className='all-test'>
      <div className='stepWrapper'>
        {labelArray.map((item, index) => (
          <Step
            key={index}
            index={index}
            label={item}
            updateStep={props?.updateStep}
            selected={props?.currentStep === index + 1}
          ></Step>
        ))}
      </div>
    </div>
  )
}

export default Stepper
