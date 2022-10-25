import { FC } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Credentials } from './Credentials';
import { ChangePassword } from './ChangePassword';

export const Login: FC = () => (
  <Routes>
    <Route path="/" element={<Credentials />} />
    <Route path="/change-password" element={<ChangePassword />} />
  </Routes>
);
