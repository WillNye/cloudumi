import { FC } from 'react';
import { Input } from 'shared/form/Input';
import { Button } from '../Button';
import styles from './Pagination.module.css';
export interface PaginationProps {
  gotoPage: (page: number) => void;
  previousPage: () => void;
  nextPage: () => void;
  canPreviousPage: boolean;
  canNextPage: boolean;
  pageCount: number;
  pageIndex: number;
  pageOptions: number[];
}

export const Pagination: FC<PaginationProps> = ({
  gotoPage,
  previousPage,
  nextPage,
  canPreviousPage,
  canNextPage,
  pageCount,
  pageIndex,
  pageOptions
}) => {
  return (
    <div className={styles.pagination}>
      <Button
        className={styles.btn}
        size="small"
        onClick={() => gotoPage(1)}
        disabled={!canPreviousPage}
      >
        {'<<'}
      </Button>
      <Button
        className={styles.btn}
        size="small"
        onClick={() => previousPage()}
        disabled={!canPreviousPage}
      >
        Previous
      </Button>
      <Button
        className={styles.btn}
        size="small"
        onClick={() => nextPage()}
        disabled={!canNextPage}
      >
        Next
      </Button>
      <Button
        className={styles.btn}
        size="small"
        onClick={() => gotoPage(pageCount)}
        disabled={!canNextPage}
      >
        {'>>'}
      </Button>
      <span>
        Page
        <strong>
          {pageIndex + 1} of {pageOptions.length}
        </strong>
      </span>
      <span className={styles.text}>
        {' '}
        | Go to page:{' '}
        <Input
          type="number"
          onChange={e => {
            const page = e.target.value ? Number(e.target.value) : pageIndex;
            gotoPage(page + 1);
          }}
          style={{ width: '100px' }}
          max={pageCount}
          min={1}
          value={pageIndex + 1}
          size="small"
        />
      </span>
      {/* <select
        value={pageSize}
        onChange={e => {
          setPageSize(Number(e.target.value));
        }}
      >
        {[10, 20, 30, 40, 50].map(pageSize => (
          <option key={pageSize} value={pageSize}>
            Show {pageSize}
          </option>
        ))}
      </select> */}
    </div>
  );
};
