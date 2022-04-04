/* eslint-disable react-hooks/exhaustive-deps */
import React, { useEffect, useState } from 'react'
import { SectionTitle, TableTopBar } from '../utils'
import { Segment } from 'semantic-ui-react'
import { Section } from 'lib/Section'

export const IntegrationSlack = () => {

  return (
    <Section title={<SectionTitle title='Slack' helpHandler='slack' />}>
      <Segment basic vertical>

      </Segment>
    </Section>
  )
}
