import styled from 'styled-components';

export const RowStatusIndicator = styled.span`
  width: 16px;
  height: 16px;
  display: block;
  border-radius: 100%;
  background-color: ${({ isActive }) => isActive ? 'green' : 'grey'};
`;
