import { FC } from 'react';
import { Route, Routes } from 'react-router-dom';
import { ChangePassword } from './ChangePassword';
import NotFound from '../../NotFound';

export const Accounts: FC = () => (
  <Routes>
    <Route path="/change-password" element={<ChangePassword />} />
    <Route path="*" element={<NotFound />} />
  </Routes>
);
