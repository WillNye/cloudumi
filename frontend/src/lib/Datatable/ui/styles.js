import styled from 'styled-components'

export const DatatableHeader = styled.div`
  font-weight: bold;
  border-bottom: 1px solid #cccccc;
  padding-bottom: 10px;
`

export const DatatableRow = styled.div`
  margin: 10px 0;
  & + & {
    border-top: 1px solid #cccccc;
    padding-top: 10px;
  }
`
