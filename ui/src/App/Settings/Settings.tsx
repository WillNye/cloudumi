import { FC } from 'react';
import { Route, Routes } from 'react-router-dom';
import NotFound from '../NotFound';
import Integrations from './Integrations';
import Accounts from './Accounts';
import General from './General';
import Individual from './Individual';

export const Settings: FC = () => (
  <Routes>
    <Route path="/" element={<General />} />
    <Route path="/integrations/" element={<Integrations />} />
    <Route path="/accounts/" element={<Accounts />} />
    <Route path="/personal" element={<Individual />} />
    <Route path="*" element={<NotFound fullPage />} />
  </Routes>
);
