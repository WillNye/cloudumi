import React from 'react'
import { CIDRBlock } from './CIDRBlock'
import { IPRestrictionToggle } from './IPRestrictionToggle'
import { ChallengeURLConfig } from './ChallengeURLConfig'
import { TrustPoliciesToggle } from './TrustPoliciesToggle'

export const General = () => {
  return (
    <>
      <ChallengeURLConfig />
      <IPRestrictionToggle />
      <CIDRBlock />
      <TrustPoliciesToggle />
    </>
  )
}
