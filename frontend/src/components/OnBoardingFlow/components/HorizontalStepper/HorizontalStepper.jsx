import React from 'react'
import './HorizontalStepper.scss'

const HorizontalStepper = (props) => {
  return (
    <div className='wrapper option-1 option-1-1'>
      <ol className='c-stepper'>
        <li className='c-stepper__item'>
          <span className='c-stepper__label'>1</span>
          <h3 className='c-stepper__title'>Connection Method</h3>
          <p className='c-stepper__desc'>Some desc text</p>
        </li>
        <li className='c-stepper__item'>
          <span className='c-stepper__label'>2</span>
          <h3 className='c-stepper__title'>Configure</h3>
          <p className='c-stepper__desc'>Some desc text</p>
        </li>
        <li className='c-stepper__item'>
          <span className='c-stepper__label'>3</span>
          <h3 className='c-stepper__title'>Login AWS & Create Stack</h3>
          <p className='c-stepper__desc'>Some desc text</p>
        </li>
        <li className='c-stepper__item'>
          <span className='c-stepper__label'>4</span>
          <h3 className='c-stepper__title'>Status</h3>
          <p className='c-stepper__desc'>Some desc text</p>
        </li>
      </ol>
    </div>
  )
}

export default HorizontalStepper
