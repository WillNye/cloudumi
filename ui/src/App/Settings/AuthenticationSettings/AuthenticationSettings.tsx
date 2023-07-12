import { Fragment, useEffect, useMemo, useState } from 'react';
import { AUTH_SETTINGS_TABS } from './constants';
import SAMLSettings from './components/SAMLSettings';
import OIDCSettings from './components/OIDCSettings';
import styles from './AuthenticationSettings.module.css';
import { Button } from 'shared/elements/Button';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  deleteOidcSettings,
  deleteSamlSettings,
  fetchAuthSettings
} from 'core/API/ssoSettings';
import { toast } from 'react-toastify';
import { invalidateSsoQueries } from './components/utils';

const AuthenticationSettings = () => {
  const [currentTab, setCurrentTab] = useState<AUTH_SETTINGS_TABS>(
    AUTH_SETTINGS_TABS.SAML
  );
  const queryClient = useQueryClient();

  const { isLoading: isLoadingAuth, data: authSettings } = useQuery({
    queryKey: ['authSettings'],
    queryFn: fetchAuthSettings,
    select: data => data.data
  });

  const { isLoading: isLoadingMutation, mutateAsync: saveMutation } =
    useMutation({
      mutationFn: async () => {
        await deleteOidcSettings();
        await deleteSamlSettings();
      },
      mutationKey: ['removeAuthSettings'],
      onSuccess: () => {
        invalidateSsoQueries(queryClient);
        toast.success('Successfully removed SAML/OIDC Settings');
      },
      onError: () => {
        toast.error('An error occured, unable remove SAML/OIDC Settings');
      }
    });

  const isLoading = useMemo(
    () => isLoadingMutation || isLoadingAuth,
    [isLoadingMutation, isLoadingAuth]
  );

  const content = useMemo(() => {
    if (currentTab === AUTH_SETTINGS_TABS.OIDC) {
      return (
        <OIDCSettings
          isFetching={isLoading}
          current={authSettings?.get_user_by_oidc}
        />
      );
    }

    if (currentTab === AUTH_SETTINGS_TABS.SAML) {
      return (
        <SAMLSettings
          isFetching={isLoading}
          current={authSettings?.get_user_by_saml}
        />
      );
    }

    return <Fragment />;
  }, [currentTab, isLoading, authSettings]);

  useEffect(() => {
    if (authSettings?.get_user_by_saml) {
      setCurrentTab(AUTH_SETTINGS_TABS.SAML);
    } else if (authSettings?.get_user_by_oidc) {
      setCurrentTab(AUTH_SETTINGS_TABS.OIDC);
    }
  }, [authSettings]);

  return (
    <div className={styles.container}>
      <div className={styles.remove}>
        <Button
          onClick={() => saveMutation()}
          color="secondary"
          variant="outline"
          disabled={isLoadingMutation}
        >
          Deactivate
        </Button>
      </div>
      <div>
        <nav className={styles.nav}>
          <ul className={styles.navList}>
            <li
              className={`${styles.navItem} ${
                currentTab === AUTH_SETTINGS_TABS.SAML && styles.isActive
              }`}
              onClick={() => setCurrentTab(AUTH_SETTINGS_TABS.SAML)}
            >
              <div className={styles.text}>SAML Settings</div>
            </li>
            <li
              className={`${styles.navItem} ${
                currentTab === AUTH_SETTINGS_TABS.OIDC && styles.isActive
              }`}
              onClick={() => setCurrentTab(AUTH_SETTINGS_TABS.OIDC)}
            >
              <div className={styles.text}>OIDC Settings</div>
            </li>
            <li
              className={`${styles.navItem} ${
                currentTab === AUTH_SETTINGS_TABS.SCIM && styles.isActive
              }`}
              onClick={() => setCurrentTab(AUTH_SETTINGS_TABS.SCIM)}
            >
              <div className={styles.text}>SCIM</div>
            </li>
          </ul>
        </nav>
      </div>
      <div className={styles.content}>{content}</div>
    </div>
  );
};

export default AuthenticationSettings;
