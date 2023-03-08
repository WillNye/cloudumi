import { FC, lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { AuthRoute } from 'core/Auth';
import { Loader } from 'shared/elements/Loader';
import './App.module.css';

const Login = lazy(() => import('./Login'));
const Settings = lazy(() => import('./Settings'));
const NotFound = lazy(() => import('./NotFound'));
const Access = lazy(() => import('./Access'));
const Dashboard = lazy(() => import('./Dashboard'));

export const App: FC = () => (
  <Suspense fallback={<Loader fullPage />}>
    <Routes>
      {/** Wrap all Route under ProtectedRoutes element */}
      <Route path="/" element={<AuthRoute />}>
        <Route path="/" element={<Dashboard />}>
          <Route path="/" element={<Access />} />
          <Route path="/settings/*" element={<Settings />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>

      {/** Wrap all Route under PublicRoutes element */}
      <Route path="/login/*" element={<Login />} />
      <Route path="*" element={<NotFound fullPage />} />
    </Routes>
  </Suspense>
);
