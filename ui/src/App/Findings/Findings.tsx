import { FC } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import NotFound from '../NotFound';
import RequestsMenu from './FindingsMenu';
import UnusedActions from './UnusedActions';
import UnusedActionDetails from './UnusedActionDetails';

export const Findings: FC = () => {
  return (
    <>
      <Helmet>
        <title>Findings</title>
      </Helmet>
      <Routes>
        <Route path="/" element={<RequestsMenu />} />
        <Route path="/unused-actions" element={<UnusedActions />} />
        <Route
          path="/unused-actions/monitor-service-role"
          element={<UnusedActionDetails />}
        />
        <Route path="*" element={<NotFound fullPage />} />
      </Routes>
    </>
  );
};
