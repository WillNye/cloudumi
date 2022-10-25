import { FC } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Credentials } from './Credentials';
import { ChangePassword } from './ChangePassword';
import { MFA } from './MFA';
import { SetupMFA } from './SetupMFA';

export const Login: FC = () => (
  <Routes>
    <Route path="/" element={<Credentials />} />
    <Route path="/change-password" element={<ChangePassword />} />
    <Route path="/mfa" element={<MFA />} />
    <Route path="/setup-mfa" element={<SetupMFA />} />
  </Routes>
);
