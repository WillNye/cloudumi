import { FC, lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import './App.module.css'

const Login = lazy(() => import('./Login'));
const NotFound = lazy(() => import('./NotFound'));

export const App: FC = () => (
  <Suspense fallback={<div>Loading...</div>}>
    <Routes>
      <Route>
        <Route path="/login" element={<Login />} />
        <Route path="/404" element={<NotFound />} />
        <Route path="/" element={<Navigate replace to="/login" />} />
      </Route>
    </Routes>
  </Suspense>
);
