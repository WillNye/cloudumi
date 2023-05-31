import { FC } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import NotFound from '../NotFound';
import RequestsMenu from './RequestsMenu';
import RequestsList from './RequestsList';
import SelfService from './SelfService';

export const Requests: FC = () => {
  return (
    <>
      <Helmet>
        <title>Requests</title>
      </Helmet>
      <Routes>
        <Route path="/" element={<RequestsMenu />} />
        <Route path="/all/" element={<RequestsList />} />
        <Route path="/create/" element={<SelfService />} />
        <Route path="*" element={<NotFound fullPage />} />
      </Routes>
    </>
  );
};
