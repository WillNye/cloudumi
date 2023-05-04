import { FC } from 'react';
import { Route, Routes } from 'react-router-dom';
import NotFound from '../NotFound';
import ResourceDetails from './ResourceDetails';
import ResourcesList from './ResourcesList';

const Resources: FC = () => (
  <Routes>
    <Route path="/" element={<ResourcesList />} />
    <Route
      path="/:provider/*"
      loader={({ params }) => {
        console.log(params['*']);
        ('one/two');
      }}
      element={<ResourceDetails />}
    />
    <Route path="*" element={<NotFound fullPage />} />
  </Routes>
);

export default Resources;
