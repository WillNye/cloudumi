import { FC, useCallback, useMemo } from 'react';
import { Input } from 'shared/form/Input';
import { Button } from '../Button';
import styles from './Pagination.module.css';

export interface PaginationProps {
  pageSize?: number;
  pageIndex?: number;
  totalCount?: number;
  handleOnPageChange?: (page: number) => void;
}

export const Pagination: FC<PaginationProps> = ({
  handleOnPageChange,
  totalCount = 1,
  pageIndex = 1,
  pageSize = 30
}) => {
  const pageCount = useMemo(
    () => Math.ceil(totalCount / pageSize),
    [totalCount, pageSize]
  );

  const canNextPage = useMemo(
    () => pageIndex >= pageCount,
    [pageCount, pageIndex]
  );
  const canPreviousPage = useMemo(() => pageIndex <= 1, [pageIndex]);

  const gotoPage = useCallback(
    page => {
      handleOnPageChange?.(page);
    },
    [handleOnPageChange]
  );

  const previousPage = useCallback(() => {
    handleOnPageChange?.(pageIndex - 1);
  }, [handleOnPageChange, pageIndex]);

  const nextPage = useCallback(() => {
    handleOnPageChange?.(pageIndex + 1);
  }, [handleOnPageChange, pageIndex]);

  return (
    <div className={styles.pagination}>
      <Button
        className={styles.btn}
        size="small"
        onClick={() => gotoPage(1)}
        disabled={canPreviousPage}
      >
        {'<<'}
      </Button>
      <Button
        className={styles.btn}
        size="small"
        onClick={previousPage}
        disabled={canPreviousPage}
      >
        Previous
      </Button>
      <Button
        className={styles.btn}
        size="small"
        onClick={nextPage}
        disabled={canNextPage}
      >
        Next
      </Button>
      <Button
        className={styles.btn}
        size="small"
        onClick={() => gotoPage(pageCount)}
        disabled={canNextPage}
      >
        {'>>'}
      </Button>
      <span>
        Page
        <strong>
          {pageIndex} of {pageCount}
        </strong>
      </span>
      <span className={styles.text}>
        {' '}
        | Go to page:{' '}
        <Input
          type="number"
          onChange={e => {
            const page = e.target.value ? Number(e.target.value) : pageIndex;
            gotoPage(page);
          }}
          style={{ width: '100px' }}
          max={pageCount}
          min={1}
          value={pageIndex}
          size="small"
        />
      </span>
      {/* <Select
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
      </Select> */}
    </div>
  );
};
