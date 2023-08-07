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
import SCIMSettings from './components/SCIMSettings/SCIMSettings';
import { Dialog } from 'shared/layers/Dialog';
import { Divider } from 'shared/elements/Divider';
import { LineBreak } from 'shared/elements/LineBreak';
import { Icon } from 'shared/elements/Icon';

const AuthenticationSettings = () => {
  const [showDialog, setShowDialog] = useState(false);
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
          oidcRedirectUrl={authSettings?.oidc_redirect_uri}
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

    if (currentTab === AUTH_SETTINGS_TABS.SCIM) {
      return <SCIMSettings isFetching={isLoading} />;
    }

    return <Fragment />;
  }, [currentTab, isLoading, authSettings]);

  useEffect(() => {
    if (authSettings?.get_user_by_saml) {
      setCurrentTab(AUTH_SETTINGS_TABS.SAML);
    } else if (authSettings?.get_user_by_oidc) {
      setCurrentTab(AUTH_SETTINGS_TABS.OIDC);
    } else if (authSettings?.scim_enabled) {
      setCurrentTab(AUTH_SETTINGS_TABS.SCIM);
    }
  }, [authSettings]);

  return (
    <div className={styles.container}>
      <div className={styles.remove}>
        <Button
          onClick={() => setShowDialog(true)}
          color="secondary"
          variant="outline"
          size="small"
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
              <div className={styles.tabHeader}>
                SAML Settings
                {authSettings?.get_user_by_saml && (
                  <Icon name="notification-success" />
                )}
              </div>
            </li>
            <li
              className={`${styles.navItem} ${
                currentTab === AUTH_SETTINGS_TABS.OIDC && styles.isActive
              }`}
              onClick={() => setCurrentTab(AUTH_SETTINGS_TABS.OIDC)}
            >
              <div className={styles.tabHeader}>
                OIDC Settings
                {authSettings?.get_user_by_oidc && (
                  <Icon name="notification-success" />
                )}
              </div>
            </li>
            <li
              className={`${styles.navItem} ${
                currentTab === AUTH_SETTINGS_TABS.SCIM && styles.isActive
              }`}
              onClick={() => setCurrentTab(AUTH_SETTINGS_TABS.SCIM)}
            >
              <div className={styles.tabHeader}>
                SCIM
                {authSettings?.scim_enabled && (
                  <Icon name="notification-success" />
                )}
              </div>
            </li>
          </ul>
        </nav>
      </div>
      <div className={styles.content}>{content}</div>
      <Dialog
        setShowDialog={setShowDialog}
        showDialog={showDialog}
        header="Deactivate SSO"
      >
        <div className={styles.modalContent}>
          <p className={styles.text}>
            Are you sure you would like to deactivate the identity and access
            management protocols?
          </p>
          <LineBreak size="large" />
          <div className={styles.modalActions}>
            <Button size="small" color="secondary" variant="outline" fullWidth>
              Cancel
            </Button>
            <Divider orientation="vertical" />
            <Button
              size="small"
              color="error"
              onClick={() => {
                saveMutation();
                setShowDialog(false);
              }}
              fullWidth
            >
              Remove
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
};

export default AuthenticationSettings;
