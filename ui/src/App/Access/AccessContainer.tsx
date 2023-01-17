import { FC, useState } from 'react';
import { Loader } from 'shared/elements/Loader';
import { Access } from './Access';
import roles from './demo.json';

export const AccessContainer: FC = () => {
  // This is where the logic that interacts w/ the backend will go
  // You should avoid putting styles/etc in this component
  // I tend to only put the loader and the error state here

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
