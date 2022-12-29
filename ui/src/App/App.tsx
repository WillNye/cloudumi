import { FC, lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { AuthRoute } from 'core/Auth';
import './App.module.css';

const Login = lazy(() => import('./Login'));
const AccountSetup = lazy(() => import('./AccountSetup'));
const NotFound = lazy(() => import('./NotFound'));
const Access = lazy(() => import('./Access'));
const Dashboard = lazy(() => import('./Dashboard'));

export const App: FC = () => (
  <Suspense fallback={<div>Loading...</div>}>
    <Routes>
      {/** Wrap all Route under ProtectedRoutes element */}
      <Route path="/" element={<AuthRoute />}>
        <Route path="/" element={<Dashboard />}>
          <Route path="/account/*" element={<AccountSetup />} />
          <Route path="/404" element={<NotFound />} />
        </Route>
      </Route>

      {/** Wrap all Route under PublicRoutes element */}
      <Route>
        <Route path="/access" element={<Access />} />
        <Route path="/login/*" element={<Login />} />
      </Route>
    </Routes>
  </Suspense>
);
