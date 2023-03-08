import { useState } from 'react';
import { Pagination } from './Pagination';

export default {
  title: 'Elements/Pagination',
  component: Pagination
};

export const Basic = () => {
  const [currentPage, setCurrentPage] = useState(1);

  return (
    <Pagination
      totalCount={30}
      pageIndex={currentPage}
      pageSize={3}
      handleOnPageChange={setCurrentPage}
    />
  );
};
