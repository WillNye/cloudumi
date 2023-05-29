import { FC } from 'react';
import { Route, Routes } from 'react-router-dom';
import NotFound from '../NotFound';
import Integrations from './Integrations';
import Accounts from './Accounts';
import SettingsMenu from './SettingsMenu';
import ProfileSettings from './ProfileSettings';
import { Helmet } from 'react-helmet-async';
import OnBoarding from './Integrations/components/CloudProviderSettings/AWSProvider/AWSOnboarding';
import AWSProvider from './Integrations/components/CloudProviderSettings/AWSProvider';
import AdminAuthRoute from 'core/Auth/AdminAuthRoute';

export const Settings: FC = () => {
  return (
    <>
      <Helmet>
        <title>Settings</title>
      </Helmet>
      <Routes>
        <Route path="/" element={<SettingsMenu />}>
          <Route path="/" element={<ProfileSettings />} />
          <Route path="/" element={<AdminAuthRoute />}>
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/integrations/aws" element={<AWSProvider />} />
            <Route
              path="/integrations/aws/onboarding"
              element={<OnBoarding />}
            />
            <Route path="/user_management" element={<Accounts />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFound fullPage />} />
      </Routes>
    </>
  );
};
