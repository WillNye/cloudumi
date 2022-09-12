import React from 'react'
import Stepper from './Stepper'
import { stepperDetails } from './constants'

const ConnectAWS = () => {
  return (
    <div className='on-boarding__stepper'>
      <Stepper stepperDetails={stepperDetails} />
    </div>
  )
}

export default ConnectAWS
