import { FC } from 'react';
import { Route, Routes } from 'react-router-dom';
import NotFound from '../../NotFound';
import Users from './Users';
import Groups from './Groups';

export const Accounts: FC = () => (
  <Routes>
    <Route path="/" element={<Users />} />
    <Route path="/groups" element={<Groups />} />
    <Route path="*" element={<NotFound />} />
  </Routes>
);
