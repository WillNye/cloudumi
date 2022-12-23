import { FC } from 'react';
import { Helmet } from 'react-helmet-async';

import css from './Access.module.css';

export interface AccessRole {
  arn: string;
  account_name: string;
  account_id: string;
  role_name: string;
  redirect_uri: string;
  inactive_tra: boolean;
}

export interface AccessQueryResult {
  totalCount: number;
  filteredCount: number;
  data: AccessRole[];
}

type AccessProps = AccessQueryResult;

export const Access: FC<AccessProps> = ({ data }) => {
  return (
    <>
      <Helmet>
        <title>Access</title>
      </Helmet>
      <div className={css.container}>
        <pre>{JSON.stringify(data, null, '\t')}</pre>
      </div>
    </>
  );
};
