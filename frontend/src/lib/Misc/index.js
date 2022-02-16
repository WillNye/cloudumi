import styled from 'styled-components';

export const RowStatusIndicator = styled.span`
  width: 16px;
  height: 16px;
  display: block;
  border-radius: 100%;
  background-color: ${({ isActive }) => isActive ? 'green' : 'grey'};
`;

export const Fill = styled.div`
  flex-grow: 1;
  flex-shrink: 0;
`;

export const Bar = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  width: 100%;
`;