import { FC, lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import { AuthRoute } from 'core/Auth';
import { Loader } from 'shared/elements/Loader';
import 'react-toastify/dist/ReactToastify.css';
import Resources from './Resources/Resources';
import ResourceDetails from './Resources/Details/ResourceDetails';

const Login = lazy(() => import('./Login'));
const Settings = lazy(() => import('./Settings'));
const NotFound = lazy(() => import('./NotFound'));
const Access = lazy(() => import('./Access'));
const Dashboard = lazy(() => import('./Dashboard'));
const EULA = lazy(() => import('./EULA'));

export const App: FC = () => (
  <Suspense fallback={<Loader fullPage />}>
    <ToastContainer theme="dark" />
    <Routes>
      {/** Wrap all Route under ProtectedRoutes element */}
      <Route path="/eula" element={<EULA />} />
      <Route path="/" element={<AuthRoute />}>
        <Route path="/" element={<Dashboard />}>
          <Route path="/" element={<Access />} />
          <Route path="/settings/*" element={<Settings />} />
          <Route path="/resources" element={<Resources />} />

          <Route
            path="/resources/:provider/*"
            loader={({ params }) => {
              console.log(params['*']); // "one/two"
            }}
            element={<ResourceDetails />}
          />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>

      {/** Wrap all Route under PublicRoutes element */}
      <Route path="/login/*" element={<Login />} />
      <Route path="*" element={<NotFound fullPage />} />
    </Routes>
  </Suspense>
);
