import { FC } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Logout } from './Logout';

export const Session: FC = () => (
  <Routes>
    <Route path="/logout" element={<Logout />} />
  </Routes>
);
