import React from 'react'
import { Link, useHistory } from 'react-router-dom'
import { Button, Icon, Label, Table } from 'semantic-ui-react'
import ReactJson from 'react-json-view'
import ReactMarkdown from 'react-markdown'

const DEFAULT_ROWS_PER_PAGE = 50

const DataTableRowsComponent = ({
  expandedRow,
  filteredData,
  tableConfig,
  activePage,
  calculateColumnSize,
  setExpandedRow,
  setRedirect,
  setTempEscalationModalData,
}) => {
  const expandNestedJson = (data) => {
    Object.keys(data).forEach((key) => {
      try {
        data[key] = JSON.parse(data[key])
      } catch (e) {
        // no-op
      }
    })
    return data
  }

  const history = useHistory()

  const handleCellClick = (e, column, entry) => {
    // This function should appropriately handle a Cell Click given a desired
    // action by the column configuration

    const onClickhandler = entry.onClick || column.onClick

    if (!onClickhandler) return

    if (
      onClickhandler.action === 'redirect' &&
      onClickhandler.type === 'temp_escalation_redirect'
    ) {
      history.push(entry['policy_request_uri'])
    }

    if (onClickhandler.action === 'redirect') {
      // TODO, change this to useHistory
      setRedirect(entry[column.key] + window.location.search || '')
    }

    if (onClickhandler.action === 'open_modal') {
      if (onClickhandler.type === 'temp_escalation_modal') {
        setTempEscalationModalData(true, entry)
      }
    }
  }

  const handleRowExpansion = (
    idx,
    expandedRow,
    filteredData,
    tableConfig,
    activePage
  ) => {
    // close expansion if there is any expanded row.
    if (expandedRow && expandedRow.index === idx + 1) {
      setExpandedRow(null)
    } else {
      const rowsPerPage = tableConfig.rowsPerPage || DEFAULT_ROWS_PER_PAGE
      // expand the row if a row is clicked.
      const filteredDataPaginated = filteredData.slice(
        (activePage - 1) * rowsPerPage,
        activePage * rowsPerPage - 1
      )

      // get an offset if there is any expanded row and trying to expand row underneath
      const offset = expandedRow && expandedRow.index < idx ? 1 : 0
      const newExpandedRow = {
        index: idx + 1 - offset,
        data: expandNestedJson(filteredDataPaginated[idx - offset]),
      }
      setExpandedRow(newExpandedRow)
    }
  }

  const rowsPerPage = tableConfig.rowsPerPage || DEFAULT_ROWS_PER_PAGE
  const filteredDataPaginated = filteredData.slice(
    (activePage - 1) * rowsPerPage,
    activePage * rowsPerPage - 1
  )

  if (expandedRow) {
    const { index, data } = expandedRow
    filteredDataPaginated.splice(index, 0, data)
  }

  // Return the list of rows after building its cells and events
  return filteredDataPaginated.map(
    (entry, ridx) => {
      // if a row is clicked then show its associated detail row.
      if (expandedRow && expandedRow.index === ridx) {
        return (
          <Table.Row key={`row-${ridx}`}>
            <Table.Cell collapsing colSpan={calculateColumnSize(tableConfig)}>
              <ReactJson
                displayDataTypes={false}
                displayObjectSize={false}
                collapseStringsAfterLength={70}
                indentWidth={2}
                name={false}
                src={expandedRow.data}
              />
            </Table.Cell>
          </Table.Row>
        )
      }

      const cells = []
      tableConfig.columns.forEach((column, cidx) => {
        if (column.type === 'daterange') {
          cells.push(
            <Table.Cell
              key={`cell-${ridx}-${cidx}`}
              collapsing
              style={column.style}
            >
              <ReactMarkdown
                children={new Date(entry[column.key] * 1000).toUTCString()}
              />
            </Table.Cell>
          )
        } else if (column.type === 'button') {
          cells.push(
            <Table.Cell
              key={`cell-${ridx}-${cidx}`}
              collapsing
              style={column.style}
            >
              <Button
                animated
                fluid
                //labelPosition='right'
                color={entry['color'] || 'blue'}
                onClick={(e) => handleCellClick(e, column, entry)}
                size='mini'
              >
                <Button.Content visible>
                  {entry['content'] || column.content}
                </Button.Content>
                <Button.Content hidden>
                  <Icon name={column.icon || 'arrow right'}></Icon>
                </Button.Content>
              </Button>
            </Table.Cell>
          )
        } else if (column.type === 'abutton') {
          cells.push(
            <Table.Cell
              key={`cell-${ridx}-${cidx}`}
              collapsing
              style={column.style}
            >
              <Button
                as='a'
                href={entry[column.key] + window.location.search || ''}
                content={entry['content'] || column.content}
                fluid
                labelPosition='right'
                icon={column.icon}
                color={entry['color'] || 'blue'}
                style={{
                  cursor: 'pointer',
                }}
                size='mini'
              />
            </Table.Cell>
          )
        } else if (column.type === 'icon') {
          cells.push(
            <Table.Cell
              key={`cell-${ridx}-${cidx}`}
              collapsing
              style={column.style}
            >
              <Icon
                onClick={(e) => handleCellClick(e, column, entry)}
                link
                name={column.icon}
              />
            </Table.Cell>
          )
        } else if (column.useLabel) {
          cells.push(
            <Table.Cell
              key={`cell-${ridx}-${cidx}`}
              collapsing
              style={column.style}
            >
              <Label>
                {entry[column.key] != null && entry[column.key].toString()}
              </Label>
            </Table.Cell>
          )
        } else if (column.type === 'link') {
          // TODO, provide an option not to send markdown format
          const value =
            entry[column.key] != null && entry[column.key].toString()
          let found = null
          try {
            found = value.match(/\[(.+?)\]\((.+?)\)/)
          } catch (e) {
            console.log(e)
          }
          if (found) {
            cells.push(
              <Table.Cell
                key={`cell-${ridx}-${cidx}`}
                collapsing
                style={column.style}
              >
                {found[2].startsWith('/') ? (
                  <Link to={found[2]}>{found[1]}</Link>
                ) : (
                  <a href={found[2]} target='_blank' rel='noreferrer'>
                    {found[1]}
                  </a>
                )}
              </Table.Cell>
            )
          } else {
            cells.push(
              <Table.Cell
                key={`cell-${ridx}-${cidx}`}
                collapsing
                style={column.style}
              >
                <ReactMarkdown
                  children={
                    entry[column.key] != null && entry[column.key].toString()
                  }
                />
              </Table.Cell>
            )
          }
        } else {
          cells.push(
            <Table.Cell
              key={`cell-${ridx}-${cidx}`}
              collapsing
              style={column.style}
            >
              <ReactMarkdown
                children={
                  entry[column.key] != null && entry[column.key].toString()
                }
              />
            </Table.Cell>
          )
        }
      })

      return (
        <Table.Row key={`row-${ridx}`}>
          {tableConfig.expandableRows && (
            <Table.Cell key={`expand-cell-${ridx}`} collapsing>
              <Icon
                link
                name={
                  expandedRow && expandedRow.index - 1 === ridx
                    ? 'caret down'
                    : 'caret right'
                }
                onClick={() =>
                  handleRowExpansion(
                    ridx,
                    expandedRow,
                    filteredData,
                    tableConfig,
                    activePage
                  )
                }
              />
            </Table.Cell>
          )}
          {cells}
        </Table.Row>
      )
    },
    [handleCellClick, handleRowExpansion]
  )
}

export default DataTableRowsComponent
