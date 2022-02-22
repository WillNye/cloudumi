import styled from 'styled-components';

export const SectionWrapper = styled.div`
  .ui.accordion .accordion .title, .ui.accordion .title {
    cursor: initial;
  }
`;

export const SectionHeader = styled.header`
  width: 100%;
  display: flex;
  align-items: center;
  ${({ hideTopBorder }) => !hideTopBorder ? `padding-top: 20px;` : ''}
  ${({ isActive }) => !isActive ? `opacity: .5;` : ''}
`;

export const SectionTitle = styled.h3`
  align-items: center;
  display: flex;
  flex: 1;
  margin: 0;
`;

export const SectionContent = styled.div``;