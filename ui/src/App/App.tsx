import { FC, lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import './App.module.css'

const Login = lazy(() => import('./Login'));
const NotFound = lazy(() => import('./NotFound'));

export const App: FC = () => (
  <Routes>
    <Suspense fallback={<div>Loading...</div>}>
      <Route>
        <Route path="/login" element={<Login />} />
        <Route path="/404" element={<NotFound />} />
        {/* <Route path="/" element={<Navigate replace to="/404" />} /> */}
      </Route>
    </Suspense>
  </Routes>
);
