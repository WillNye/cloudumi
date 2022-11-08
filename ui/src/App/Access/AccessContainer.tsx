import { FC } from 'react';
import { Access, AccessRole } from './Access';
import demoData from './demo.json';

export const AccessContainer: FC = () => {
  // This is where the logic that interacts w/ the backend will go
  // You should avoid putting styles/etc in this component
  // I tend to only put the loader and the error state here

  // Example:
  // const { data, loading } = useQuery<AccessContainerQuery, AccessContainerQueryVariables>(ACCESS_QUERY, {});
  // if (loading) {
  //  return <Loader />;
  // }

  const data = demoData as unknown as AccessRole[];

  return (
    <Access
      data={data}
      totalCount={data.length}
      filteredCount={0}
    />
  );
};

