import { FC } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Credentials } from './Credentials';
import { CompleteNewPassword } from './CompleteNewPassword';
import { SetupMFA } from './SetupMFA';
import { MFA } from './MFA';

export const Login: FC = () => (
  <Routes>
    <Route path="/" element={<Credentials />} />
    <Route path="/complete-password" element={<CompleteNewPassword />} />
    <Route path="/setup-mfa" element={<SetupMFA />} />
    <Route path="/mfa" element={<MFA />} />
  </Routes>
);
