import React, { useState } from 'react';
import { Accordion, Button } from 'semantic-ui-react';
import { SectionContent, SectionHeader, SectionTitle } from './styles';

export const CollapsibleSection = ({ defaultActive, title, children, hideTopBorder, forceRenderContent }) => {

  // forceRenderContent: Render content without wait to active status

  const [isActive, setActiveIndex] = useState(defaultActive);

  const handleClick = () => {
    setActiveIndex(!isActive);
  };

  return (
    <Accordion fluid>
      <Accordion.Title
        active={isActive}>
        <SectionHeader hideTopBorder={hideTopBorder} isActive={isActive}>
          <SectionTitle>{title}</SectionTitle>
          <Button onClick={handleClick} icon="dropdown" />
        </SectionHeader>
      </Accordion.Title>
      <Accordion.Content active={isActive}>
        <SectionContent>
          {forceRenderContent ? children : (isActive && children)}
        </SectionContent>
      </Accordion.Content>
    </Accordion>
  );
};
