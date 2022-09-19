import React from 'react'
import { useMemo } from 'react'
import { Divider } from 'semantic-ui-react'
import './HorizontalStepper.scss'

const Step = ({ id, header, subHeader, activeId }) => {
  const classes = useMemo(() => {
    if (activeId === id) {
      return 'c-stepper-active'
    }
    if (activeId > id) {
      return 'c-stepper-complete'
    }
    return ''
  }, [activeId, id])

  return (
    <li className={`c-stepper__item ${classes}`}>
      <span className='c-stepper__label'>{id}</span>
      <h3 className='c-stepper__title'>{header}</h3>
      <p className='c-stepper__desc'>{subHeader}</p>
    </li>
  )
}

const HorizontalStepper = ({ steps, activeId }) => {
  return (
    <div className='wrapper option-1 option-1-1'>
      <ol className='c-stepper'>
        {steps.map((step) => (
          <Step {...step} activeId={activeId} />
        ))}
      </ol>
      <Divider horizontal />
    </div>
  )
}

export default HorizontalStepper
