import { useState, useEffect, useMemo } from 'react';
import { Button } from 'shared/elements/Button';
import { toast } from 'react-toastify';
import {
  ScimSettingsData,
  disableScimSettings,
  enableScimSettings,
  fetchScimSettings
} from 'core/API/ssoSettings';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Segment } from 'shared/layout/Segment';
import { LineBreak } from 'shared/elements/LineBreak';
import { Notification, NotificationType } from 'shared/elements/Notification';
import styles from '../../AuthenticationSettings.module.css';

const SCIMSettings = ({ isFetching }) => {
  const [scimData, setScimData] = useState<ScimSettingsData | null>(null);

  const queryClient = useQueryClient();

  const {
    data: scimSettings,
    isLoading,
    isError
  } = useQuery({
    queryKey: ['scimSettings'],
    queryFn: fetchScimSettings,
    select: data => data.data
  });

  useEffect(() => {
    if (isError) {
      toast.error('Failed to load SCIM settings');
    }
  }, [isError]);

  useEffect(() => {
    setScimData(scimSettings?.data);
  }, [scimSettings]);

  const handleDisableScim = useMutation({
    mutationFn: disableScimSettings,
    mutationKey: ['disableScimSettings'],
    onSuccess: response => {
      if (response.data.status === 'success') {
        queryClient.invalidateQueries({ queryKey: ['authSettings'] });
        toast.success('SCIM settings disabled');
        setScimData(null);
      }
    },
    onError: () => toast.error('Failed to disable SCIM settings')
  });

  const handleNewToken = useMutation({
    mutationFn: enableScimSettings,
    mutationKey: ['enableScimSettings'],
    onSuccess: response => {
      if (response.data.status === 'success') {
        queryClient.invalidateQueries({ queryKey: ['authSettings'] });
        toast.success('New SCIM token generated');
        setScimData(response.data.data);
      } else {
        toast.error(response.data.reason);
      }
    },
    onError: () => toast.error('Failed to generate new SCIM token')
  });

  const isPageLoading = useMemo(() => {
    return (
      isLoading ||
      isFetching ||
      handleNewToken.isLoading ||
      handleDisableScim?.isLoading
    );
  }, [isLoading, isFetching, handleNewToken, handleDisableScim]);

  return (
    <Segment isLoading={isPageLoading}>
      <h4>Generate SCIM Configuration</h4>
      <LineBreak />
      <p className={styles.text}>
        SCIM (System for Cross-domain Identity Management) is used for
        automating the exchange of user identity information between identity
        domains.
      </p>
      <LineBreak size="small" />
      {scimData?.scim_enabled ? (
        <div className={styles.text}>
          <p>SCIM is already enabled for this account.</p>
          <p>
            If you wish to regenerate your SCIM bearer token, please delete and
            recreate the configuration.
          </p>
          <LineBreak />
          <Button
            size="small"
            onClick={async () => await handleDisableScim.mutateAsync()}
          >
            Disable SCIM
          </Button>
          <LineBreak />
        </div>
      ) : (
        <>
          <LineBreak />
          <Button
            size="small"
            onClick={async () => await handleNewToken.mutateAsync()}
          >
            Generate New SCIM Token
          </Button>
          <LineBreak />
        </>
      )}
      {scimData?.scim_secret && (
        <>
          <LineBreak />
          <h5 className={styles.text}>SCIM Token</h5>
          <LineBreak size="small" />
          <Notification
            header="Please copy this token. You
          will not be able to see it again."
            type={NotificationType.WARNING}
            fullWidth
            showCloseIcon={false}
          />
          <div className={styles.blockContent}>{scimData.scim_secret}</div>
        </>
      )}

      {scimData?.scim_enabled && scimData?.scim_url && (
        <>
          <LineBreak />

          <h5 className={styles.text}>SCIM URL</h5>
          <div className={styles.blockContent}>{scimData.scim_url}</div>
        </>
      )}
    </Segment>
  );
};

export default SCIMSettings;
