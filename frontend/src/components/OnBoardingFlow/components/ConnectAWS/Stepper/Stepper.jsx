import React from 'react'
import './Stepper.scss'

const Stepper = () => {
  return (
    <div
      // key={index}
      // className={
      //   index !== newStep.length - 1
      //     ? "w-full flex items-center"
      //     : "flex items-center"
      // }
      className='stepper__step'
    >
      <div className='stepper__step__circle'>
        <div
          // className={`rounded-full transition duration-500 ease-in-out border-2 border-gray-300 h-12 w-12
          //  flex items-center justify-center py-3  ${
          //   step.selected
          //     ? "bg-green-600 text-white font-bold border border-green-600 "
          //     : ""
          // }`}
          className='stepper__step__number'
        >
          {/* {step.completed ? (
              <span className="text-white font-bold text-xl">&#10003;</span>
            ) : (
              index + 1
            )} */}
          1
        </div>
        <div
          // className={`absolute top-0  text-center mt-16 w-32 text-xs font-medium uppercase ${
          //   step.highlighted ? "text-gray-900" : "text-gray-400"
          // }`}
          className='stepper__step__text'
        >
          {/* {step.description} */}
          Test
        </div>
      </div>
      <div
        // className={`flex-auto border-t-2 transition duration-500 ease-in-out  ${
        //   step.completed ? "border-green-600" : "border-gray-300 "
        // }  `}
        className='stepper__step__line'
      ></div>
    </div>
  )
}

export default Stepper
