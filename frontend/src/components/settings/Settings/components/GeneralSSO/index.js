import React from 'react';
import { CollapsibleSection } from '../../../../../lib/CollapsibleSection';
import { ScreenHeading } from '../../../../../lib/Screen/styles';
import { generateTitle } from '../utils';

export const GeneralSSO = () => {

  return (
    <>

      <ScreenHeading>
        Single Sign-On
      </ScreenHeading>

      <CollapsibleSection
        title={generateTitle('External Identify Provider', 'external-identify-provider')}
        defaultActive>
        SSO
      </CollapsibleSection>

    </>
  );
};