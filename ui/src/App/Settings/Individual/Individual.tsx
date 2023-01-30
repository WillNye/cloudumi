import { FC } from 'react';
import { Route, Routes } from 'react-router-dom';
import NotFound from '../../NotFound';

export const Individual: FC = () => (
  <Routes>
    <Route path="*" element={<NotFound fullPage />} />
  </Routes>
);
