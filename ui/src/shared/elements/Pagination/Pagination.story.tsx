import { useState } from 'react';
import { Pagination } from './Pagination';

export default {
  title: 'Elements/Pagination',
  component: Pagination
};

export const Basic = () => {
  const [currentPage, setCurrentPage] = useState(3);
  const totalPages = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

  return (
    <Pagination
      gotoPage={setCurrentPage}
      previousPage={() => setCurrentPage(page => page - 1)}
      nextPage={() => setCurrentPage(page => page + 1)}
      canPreviousPage={currentPage !== 1}
      canNextPage={currentPage !== totalPages.length}
      pageCount={totalPages.length}
      pageIndex={currentPage - 1}
      pageOptions={totalPages}
    />
  );
};
