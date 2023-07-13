import {
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react';
import classNames from 'classnames';
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  ColumnDef,
  flexRender,
  getSortedRowModel,
  SortingState
} from '@tanstack/react-table';
import styles from './Table.module.css';
import { Loader } from '../Loader';
import { EmptyState } from '../EmptyState';
import { Checkbox } from 'shared/form/Checkbox';
import { Pagination } from '../Pagination';
import { LineBreak } from '../LineBreak';
import { Icon } from '../Icon';
import { Menu } from 'shared/layers/Menu';

interface TableProps<D> {
  spacing?: 'expanded' | 'compact' | 'normal';
  columns: ColumnDef<D, any>[];
  data: D[];
  border?: 'basic' | 'celled' | 'row';
  striped?: boolean;
  enableRowSelection?: boolean;
  isLoading?: boolean;
  showPagination?: boolean;
  noResultsComponent?: ReactNode;
  enableColumnVisibility?: boolean;
  totalCount?: number;
  pageSize?: number;
  pageIndex?: number;
  enableSorting?: boolean;
  handleSelectRows?: (data: D[]) => void;
  handleOnSort?: (data: SortingState) => void;
  handleOnPageChange?: (pageIndex: number) => void;
}

export const Table = <T, D>({
  columns,
  data,
  spacing = 'normal',
  striped = false,
  border,
  enableRowSelection = false,
  enableColumnVisibility = false,
  isLoading = false,
  showPagination = false,
  enableSorting = false,
  totalCount,
  pageSize,
  pageIndex,
  noResultsComponent,
  handleOnSort,
  handleSelectRows,
  handleOnPageChange
}: TableProps<D>) => {
  const columnsRef = useRef();

  const [rowSelection, setRowSelection] = useState({});
  const [columnVisibility, setColumnVisibility] = useState({});
  const [isColumnMenuOpen, setIsColumnMenuOpen] = useState(false);
  const [sorting, setSorting] = useState<SortingState>([]);

  const classes = classNames(styles.table, {
    [styles[spacing]]: spacing,
    [styles.striped]: striped,
    [styles[border]]: border
  });

  useEffect(
    function onUpdateSort() {
      handleOnSort?.(sorting);
    },
    [handleOnSort, sorting]
  );

  const formattedColumns = useMemo(() => {
    if (enableRowSelection) {
      return [
        {
          id: 'select',
          enableSorting: false,
          header: ({ table }) => (
            <Checkbox
              {...{
                checked: table.getIsAllRowsSelected(),
                indeterminate: table.getIsSomeRowsSelected(),
                onChange: table.getToggleAllRowsSelectedHandler()
              }}
            />
          ),
          cell: ({ row }) => (
            <div>
              <Checkbox
                {...{
                  checked: row.getIsSelected(),
                  disabled: !row.getCanSelect(),
                  indeterminate: row.getIsSomeSelected(),
                  onChange: row.getToggleSelectedHandler()
                }}
              />
            </div>
          )
        },
        ...columns
      ];
    }
    return columns;
  }, [columns, enableRowSelection]);

  const onChange = useCallback(value => {
    setColumnVisibility(value);
  }, []);

  const table = useReactTable({
    data,
    columns: formattedColumns,
    state: {
      rowSelection,
      columnVisibility,
      sorting
    },
    onSortingChange: setSorting,
    manualSorting: true,
    enableRowSelection,
    onRowSelectionChange: setRowSelection,
    getSortedRowModel: getSortedRowModel(),
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: onChange,
    enableSorting,
    debugTable: true,
    debugHeaders: true,
    debugColumns: true
  });

  const shouldShowPagination = useMemo(() => {
    return Boolean(showPagination && !isLoading);
  }, [showPagination, isLoading]);

  return (
    <>
      <table className={classes}>
        <thead>
          {table.getHeaderGroups().map(headerGroup => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map(header => {
                console.log(header.column);
                return (
                  <th
                    key={header.id}
                    colSpan={header.colSpan}
                    className={styles.tableHead}
                  >
                    {header.isPlaceholder ? null : (
                      <div
                        className={classNames(styles.tableHeader, {
                          [styles.pointer]: header.column.getCanSort()
                        })}
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                        {{
                          asc: <Icon size="large" name="sort-ascending" />,
                          desc: <Icon size="large" name="sort-descending" />
                        }[header.column.getIsSorted() as string] ?? null}
                        {/* {header.column.getCanFilter() ? (
                          <div>
                            <Filter column={header.column} table={table} />
                          </div>
                        ) : null} */}
                      </div>
                    )}
                  </th>
                );
              })}
              {enableColumnVisibility && (
                <th className={styles.columnsDropdown}>
                  <span ref={columnsRef}>
                    <Icon
                      className={styles.columnsDropdownIcon}
                      onClick={() => setIsColumnMenuOpen(isOpen => !isOpen)}
                      name="list-view"
                      size="large"
                    />
                  </span>
                  <Menu
                    open={isColumnMenuOpen}
                    onClose={() => setIsColumnMenuOpen(false)}
                    reference={columnsRef}
                  >
                    {table.getAllLeafColumns().map(column => {
                      return (
                        <div
                          className={styles.columnsDropdownItem}
                          key={column.id}
                        >
                          <Checkbox
                            {...{
                              checked: column.getIsVisible(),
                              onChange: column.getToggleVisibilityHandler()
                            }}
                          />
                          <span className={styles.itemLabel}>{column.id}</span>
                        </div>
                      );
                    })}
                  </Menu>
                </th>
              )}
            </tr>
          ))}
        </thead>
        {isLoading ? (
          <tbody className={styles.loader}>
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
        ) : table.getRowModel().rows?.length ? (
          <tbody>
            {table.getRowModel().rows.map(row => {
              return (
                <tr key={row.id}>
                  {row.getVisibleCells().map(cell => {
                    return (
                      <td key={cell.id}>
                        <div>
                          {cell?.column?.id === 'select'
                            ? flexRender(
                                cell.column.columnDef.cell,
                                cell.getContext()
                              )
                            : (cell.getValue() as ReactNode)}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        ) : (
          <tbody className={styles.loader}>
            <tr>
              <td colSpan={columns.length}>
                <div className={styles.tableEmpty}>
                  {noResultsComponent || <EmptyState />}
                </div>
              </td>
            </tr>
          </tbody>
        )}
      </table>
      {shouldShowPagination && (
        <>
          <LineBreak />
          <Pagination
            pageSize={pageSize}
            pageIndex={pageIndex}
            totalCount={totalCount}
            handleOnPageChange={handleOnPageChange}
          />
        </>
      )}
    </>
  );
};
