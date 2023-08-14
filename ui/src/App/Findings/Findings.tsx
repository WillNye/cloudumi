import { FC } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import NotFound from '../NotFound';
import RequestsMenu from './FindingsMenu';

export const Findings: FC = () => {
  return (
    <>
      <Helmet>
        <title>Findings</title>
      </Helmet>
      <Routes>
        <Route path="/" element={<RequestsMenu />} />
        <Route path="*" element={<NotFound fullPage />} />
      </Routes>
    </>
  );
};
