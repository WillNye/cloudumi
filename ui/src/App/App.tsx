import { FC, lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import './App.module.css'

const Login = lazy(() => import('./Login'));

export const App: FC = () => (
  <Routes>
    <Suspense fallback={<div>Loading...</div>}>
      <Route>
        <Route path="/" element={<div />} />
        <Route path="/login" element={<Login />} />
      </Route>
    </Suspense>
  </Routes>
);

