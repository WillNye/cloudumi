import { FC, lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import { AuthRoute } from 'core/Auth';
import { Loader } from 'shared/elements/Loader';
import 'react-toastify/dist/ReactToastify.css';
import ChallengeValidator from './ChallengeValidator';
import Downloads from './Downloads/Downloads';

const Login = lazy(() => import('./Login'));
const Settings = lazy(() => import('./Settings'));
const Requests = lazy(() => import('./Requests'));
const Findings = lazy(() => import('./Findings'));
const Resources = lazy(() => import('./Resources'));
const NotFound = lazy(() => import('./NotFound'));
const Access = lazy(() => import('./Access'));
const Dashboard = lazy(() => import('./Dashboard'));
const EULA = lazy(() => import('./EULA'));
const Logout = lazy(() => import('./Logout'));
const SignInToRole = lazy(
  () => import('./Access/components/common/SignInToRole/SignInToRole')
);

export const App: FC = () => (
  <Suspense fallback={<Loader fullPage />}>
    <ToastContainer theme="dark" />
    <Routes>
      {/** Wrap all Route under ProtectedRoutes element */}
      <Route path="/eula" element={<EULA />} />
      <Route path="/logout" element={<Logout />} />
      <Route path="/" element={<AuthRoute />}>
        <Route path="/" element={<Dashboard />}>
          <Route path="/" element={<Access />} />
          <Route path="/resources/*" element={<Resources />} />
          <Route path="/settings/*" element={<Settings />} />
          <Route path="/requests/*" element={<Requests />} />
          <Route path="/findings/*" element={<Findings />} />
          <Route path="/role/*" element={<SignInToRole />} />
          <Route path="/downloads" element={<Downloads />} />
          <Route
            path="/challenge_validator/:challengeToken"
            element={<ChallengeValidator />}
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
