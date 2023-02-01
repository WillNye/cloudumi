import { FC } from 'react';
import { Route, Routes } from 'react-router-dom';
import NotFound from '../NotFound';
import Integrations from './Integrations';
import Accounts from './Accounts';
import SettingsMenu from './SettingsMenu';
import ProfileSettings from './ProfileSettings';
import { Helmet } from 'react-helmet-async';

export const Settings: FC = () => (
  <>
    <Helmet>
      <title>Settings</title>
    </Helmet>
    <Routes>
      <Route path="/" element={<SettingsMenu />} />
      <Route path="/integrations" element={<Integrations />} />
      <Route path="/profile" element={<ProfileSettings />} />
      <Route path="/accounts/*" element={<Accounts />} />
      <Route path="*" element={<NotFound fullPage />} />
    </Routes>
  </>
);
