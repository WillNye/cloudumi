import React, { useState } from 'react';
import { Accordion, Button } from 'semantic-ui-react';
import { CollapsibleWrapper, CollapsibleContent, CollapsibleHeader, CollapsibleTitle } from './styles';

export const CollapsibleSection = ({
  defaultActive,
  title,
  children,
  hideTopBorder,
  forceRenderContent
}) => {

  // forceRenderContent: Render content without wait to active status

  const [isActive, setActiveIndex] = useState(defaultActive);

  const handleClick = () => {
    setActiveIndex(!isActive);
  };

  return (
    <CollapsibleWrapper>
      <Accordion fluid>
        <Accordion.Title
          active={isActive}>
          <CollapsibleHeader hideTopBorder={hideTopBorder} isActive={isActive}>
            <CollapsibleTitle>{title}</CollapsibleTitle>
            <Button onClick={handleClick} icon="dropdown" />
          </CollapsibleHeader>
        </Accordion.Title>
        <Accordion.Content active={isActive}>
          <CollapsibleContent>
            {forceRenderContent ? children : (isActive && children)}
          </CollapsibleContent>
        </Accordion.Content>
      </Accordion>
    </CollapsibleWrapper>
  );
};
