import React from 'react'
import { CIDRBlock } from './CIDRBlock'
import { IPRestrictionToggle } from './IPRestrictionToggle'

export const General = () => {
  return (
    <>
      <IPRestrictionToggle />
      <CIDRBlock />
    </>
  )
}
