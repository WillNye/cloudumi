import { useMemo } from 'react';
import classNames from 'classnames';
import {
  useTable,
  useFilters,
  useRowSelect,
  usePagination,
  useSortBy
} from 'react-table';
import { IndeterminateCheckbox } from './Filters';
import styles from './Table.module.css';

interface TableProps<T, D> {
  spacing?: 'spaced' | 'compact';
  columns: T[];
  data: D[];
  border?: 'basic' | 'celled';
  striped?: boolean;
  selectable?: boolean;
}

export const Table = <T, D>({
  columns,
  data,
  spacing,
  striped = false,
  border,
  selectable = false
}: TableProps<T, D>) => {
  const classes = classNames(styles.table, {
    [styles[spacing]]: spacing,
    [styles.striped]: striped,
    [styles[border]]: border
  });

  const defaultColumn = useMemo(
    () => ({
      Filter: <></>
    }),
    []
  );

  const { getTableProps, getTableBodyProps, headerGroups, rows, prepareRow } =
    useTable(
      {
        columns,
        data,
        defaultColumn
      },
      useFilters,
      useSortBy,
      usePagination,
      useRowSelect,

      // TODO: Transfer to a separate custom hook file
      hooks => {
        if (selectable) {
          hooks.visibleColumns.push(columns => [
            // Let's make a column for selection
            {
              id: 'selection',
              // The header can use the table's getToggleAllRowsSelectedProps method
              // to render a checkbox
              Header: ({ getToggleAllPageRowsSelectedProps }) => (
                <div>
                  <IndeterminateCheckbox
                    {...getToggleAllPageRowsSelectedProps()}
                  />
                </div>
              ),
              // The cell can use the individual row's getToggleRowSelectedProps method
              // to the render a checkbox
              Cell: ({ row }) => (
                <div>
                  <IndeterminateCheckbox {...row.getToggleRowSelectedProps()} />
                </div>
              )
            },
            ...columns
          ]);
        }
      }
    );

  return (
    <table {...getTableProps()} className={classes}>
      <thead>
        {headerGroups.map((headerGroup, index) => (
          <tr key={index} {...headerGroup.getHeaderGroupProps()}>
            {headerGroup.headers.map((column, idx) => (
              <th
                key={idx}
                {...column.getHeaderProps({
                  ...(column?.sortable && { ...column.getSortByToggleProps() }),
                  style: {
                    minWidth: column.minWidth,
                    width: column.width,
                    maxWidth: column.maxWidth
                  }
                })}
                className={styles.th}
              >
                {column.render('Header')}

                {/* TODO: Use icons for to show asc and desc order  */}
                <span>
                  {column.isSorted
                    ? column.isSortedDesc
                      ? 'DESC'
                      : 'ASC'
                    : ''}
                </span>
                <div>{column.canFilter ? column.render('Filter') : null}</div>
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody {...getTableBodyProps()}>
        {rows.map((row, index) => {
          prepareRow(row);
          return (
            <tr key={index} {...row.getRowProps()} className={styles.tr}>
              {row.cells.map((cell, idx) => {
                return (
                  <td key={idx} {...cell.getCellProps()} className={styles.td}>
                    {cell.render('Cell')}
                  </td>
                );
              })}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
};
