import styled from 'styled-components';

export const SectionHeader = styled.header`
  width: 100%;
  display: flex;
  align-items: center;
  ${({ hideTopBorder }) => !hideTopBorder ? `
    padding-top: 20px;
    border-top: 1px solid;
  ` : ''}
  ${({ isActive }) => !isActive ? `opacity: .5;` : ''}
`;

export const SectionTitle = styled.h3`
  align-items: center;
  display: flex;
  flex: 1;
  margin: 0;
`;

export const SectionContent = styled.div``;