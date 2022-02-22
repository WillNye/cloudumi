import React, { useState } from 'react';
import { Accordion, Button } from 'semantic-ui-react';
import { SectionWrapper, SectionContent, SectionHeader, SectionTitle } from './styles';

export const Section = ({
  defaultActive = true,
  title,
  children,
  hideTopBorder,
  forceRenderContent,
  isCollapsible
}) => {

  // forceRenderContent: Render content without wait to active status

  const [isActive, setActiveIndex] = useState(defaultActive);

  const handleClick = () => {
    setActiveIndex(!isActive);
  };

  return (
    <SectionWrapper>
      <Accordion fluid>
        <Accordion.Title active={isActive}>
          <SectionHeader hideTopBorder={hideTopBorder} isActive={isActive}>
            <SectionTitle>{title}</SectionTitle>            
            {isCollapsible && <Button onClick={handleClick} icon="dropdown" />}
          </SectionHeader>
        </Accordion.Title>
        <Accordion.Content active={isActive}>
          <SectionContent>
            {forceRenderContent ? children : (isActive && children)}
          </SectionContent>
        </Accordion.Content>
      </Accordion>
    </SectionWrapper>
  );
};
