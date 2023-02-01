import { FC, useEffect, useState } from 'react';
import { Loader } from 'shared/elements/Loader';
import { Access } from './Access';
import roles from './demo.json';

export const AccessContainer: FC = () => {
  const [isLoading, setIsLoading] = useState(false);

  if (isLoading) {
    return <Loader />;
  }

  return (
    <Access
      data={roles.data}
      totalCount={roles.totalCount}
      filteredCount={roles.filteredCount}
    />
  );
};
