import { Fragment, useMemo } from 'react';
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
import { Icon } from '../Icon';
import { Loader } from '../Loader';
import { EmptyState } from '../EmptyState';

interface TableProps<T, D> {
  spacing?: 'expanded' | 'compact';
  columns: T[];
  data: D[];
  border?: 'basic' | 'celled' | 'row';
  striped?: boolean;
  selectable?: boolean;
  isLoading?: boolean;
}

export const Table = <T, D>({
  columns,
  data,
  spacing,
  striped = false,
  border,
  selectable = false,
  isLoading = false
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
                  style: {
                    minWidth: column.minWidth,
                    width: column.width,
                    maxWidth: column.maxWidth
                  },
                  ...(column?.sortable && {
                    ...column.getSortByToggleProps()
                  })
                })}
                className={styles.th}
              >
                <div className={styles.center}>
                  <span>{column.render('Header')}</span>
                  <span>
                    {column.isSorted ? (
                      column.isSortedDesc ? (
                        <Icon name="sort-descending" size="large" />
                      ) : (
                        <Icon name="sort-ascending" size="large" />
                      )
                    ) : (
                      <Fragment />
                    )}
                  </span>
                </div>
                <div>{column.canFilter ? column.render('Filter') : null}</div>
              </th>
            ))}
          </tr>
        ))}
      </thead>
      {isLoading ? (
        <tbody>
          <tr>
            <td colSpan={columns.length}>
              <div className={styles.tableLoader}>
                <div>
                  <Loader />
                  <div className={styles.loaderText}>Loading...</div>
                </div>
              </div>
            </td>
          </tr>
        </tbody>
      ) : rows.length ? (
        <tbody {...getTableBodyProps()} className={styles.tableBody}>
          {rows.map((row, index) => {
            prepareRow(row);
            return (
              <tr key={index} {...row.getRowProps()} className={styles.tr}>
                {row.cells.map((cell, idx) => {
                  return (
                    <td
                      key={idx}
                      {...cell.getCellProps()}
                      className={styles.td}
                    >
                      {cell.render('Cell')}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      ) : (
        <tbody>
          <tr>
            <td colSpan={columns.length}>
              <div className={styles.tableEmpty}>
                <EmptyState />
              </div>
            </td>
          </tr>
        </tbody>
      )}
    </table>
  );
};
