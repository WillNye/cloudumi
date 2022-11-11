import { useQuery } from '@apollo/client';
import { GET_ELIGIBLE_ROLES_QUERY } from 'core/graphql';
import { FC } from 'react';
import { Loader } from 'shared/elements/Loader';
import { Access } from './Access';

export const AccessContainer: FC = () => {
  // This is where the logic that interacts w/ the backend will go
  // You should avoid putting styles/etc in this component
  // I tend to only put the loader and the error state here

  const { data: response, loading, error } = useQuery(GET_ELIGIBLE_ROLES_QUERY);

  const allEligibleRoles = response?.roles;

  if (loading) {
    return <Loader />;
  }

  return (
    <>
      {allEligibleRoles && (
        <Access
          data={allEligibleRoles.data}
          totalCount={allEligibleRoles.totalCount}
          filteredCount={allEligibleRoles.filteredCount}
        />
      )}
      {error && <div>An error occured</div>}
    </>
  );
};
