import { FC } from 'react';
import EmptyStateImage from '../../../assets/illustrations/search.svg';
import css from './EmptyState.module.css';

export const EmptyState: FC = () => {
  return (
    <div className={css.container}>
      <img src={EmptyStateImage} />
      <h3>No result found!</h3>
      <h5 className={css.text}>No results found that match the above query</h5>
    </div>
  );
};
