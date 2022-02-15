import React, { useMemo } from 'react';

import {
  useTable,
  useResizeColumns,
  useFlexLayout,
  useRowSelect,
} from 'react-table';
import { DatatableHeader, DatatableRow } from './ui/styles';
import { EmptyState } from './ui/utils';

const headerProps = (props, { column }) => getStyles(props, column.align);

const cellProps = (props, { cell }) => getStyles(props, cell.column.align);

const getAlign = (align) => align === 'right' ? 'flex-end' : align === 'center' ? 'center' : 'flex-start';

const getStyles = (props, align = 'left') => [props, {
  style: {
    justifyContent: getAlign(align),
    alignItems: 'center',
    display: 'flex',
    flexWrap: 'nowrap'
  }
}];

function Table({ columns, data }) {

  const defaultColumn = React.useMemo(() => ({
    // When using the useFlexLayout:
    minWidth: 30, // minWidth is only used as a limit for resizing
    width: 150, // width is used for both the flex-basis and flex-grow
    maxWidth: 200, // maxWidth is only used as a limit for resizing
  }), []);

  const { getTableProps, headerGroups, rows, prepareRow } = useTable({
    columns,
    data,
    defaultColumn,
  },
  useResizeColumns,
  useFlexLayout,
  useRowSelect);

  return (
    <div {...getTableProps()} className="table">
      <div>
        {headerGroups.map(headerGroup => (
          <div
            {...headerGroup.getHeaderGroupProps()}
            className="tr">
            {headerGroup.headers.map(column => (
              <DatatableHeader {...column.getHeaderProps(headerProps)} className="th">
                {column.render('Header')}
                {/* Use column.getResizerProps to hook up the events correctly */}
                {column.canResize && (
                  <div
                    {...column.getResizerProps()}
                    className={`resizer ${
                      column.isResizing ? 'isResizing' : ''
                    }`}
                  />
                )}
              </DatatableHeader>
            ))}
          </div>
        ))}
      </div>
      <div className="tbody">
        {rows.map(row => {
          prepareRow(row)
          return (
            <DatatableRow {...row.getRowProps()} className="tr">
              {row.cells.map(cell => {
                return (
                  <div {...cell.getCellProps(cellProps)} className="td">
                    {cell.render('Cell')}
                  </div>
                )
              })}
            </DatatableRow>
          )
        })}
      </div>
    </div>
  );
};

const Datatable = ({ data, columns, emptyState }) => {
  
  const memoizedData = useMemo(() => data, [data]);
  const memoizedColumns = useMemo(() => columns, [columns]);

  const renderTable = <Table data={memoizedData} columns={memoizedColumns} />;

  const renderEmptyState = <EmptyState {...emptyState} />;

  const hasData = data?.length > 0;

  return hasData ? renderTable : renderEmptyState;
};

export default Datatable;