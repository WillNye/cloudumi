import { FC } from 'react';
import { Route, Routes } from 'react-router-dom';
import { ChangePassword } from './ChangePassword';

export const AccountSetup: FC = () => (
  <Routes>
    <Route path="/change-password" element={<ChangePassword />} />
  </Routes>
);
