import React from 'react';
import { Section } from 'lib/Section';
import { ScreenHeading } from 'lib/Screen/styles';
import { SectionTitle } from '../utils';
import { Groups } from './components/Groups';
import { Users } from './components/Users';

export const GeneralUsers = () => {

  return (
    <>

      <ScreenHeading>
        Users and Groups
      </ScreenHeading>

      <Section title={<SectionTitle title="Users" />}>
        <Users />
      </Section>

      <Section title={<SectionTitle title="Groups" />}>
        <Groups />
      </Section>

    </>
  );
};