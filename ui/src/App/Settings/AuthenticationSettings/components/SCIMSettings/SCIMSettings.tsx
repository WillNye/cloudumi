import React, { useState, useEffect } from 'react';
import { Button } from 'shared/elements/Button';
import { toast } from 'react-toastify';
import {
  ScimSettingsData,
  disableScimSettings,
  enableScimSettings,
  fetchScimSettings
} from 'core/API/ssoSettings';
import { useMutation, useQuery } from '@tanstack/react-query';

const SCIMSettings = ({ isFetching }) => {
  const [scimData, setScimData] = useState<ScimSettingsData | null>(null);

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
        toast.success('New SCIM token generated');
        setScimData(response.data.data);
      } else {
        toast.error(response.data.reason);
      }
    },
    onError: () => toast.error('Failed to generate new SCIM token')
  });

  return (
    <div>
      <h2>Generate SCIM Configuration</h2>
      <p>
        SCIM (System for Cross-domain Identity Management) is used for
        automating the exchange of user identity information between identity
        domains.
      </p>

      {scimData?.scim_enabled ? (
        <>
          <p>SCIM is already enabled for this account.</p>
          <p>
            If you wish to regenerate your SCIM bearer token, please delete and
            recreate the configuration.
          </p>
          <Button onClick={async () => await handleDisableScim.mutateAsync()}>
            Disable SCIM
          </Button>
        </>
      ) : (
        <>
          <Button onClick={async () => await handleNewToken.mutateAsync()}>
            Generate New SCIM Token
          </Button>
        </>
      )}

      {scimData?.scim_secret && (
        <p>
          Your SCIM token: {scimData.scim_secret}. Please copy this token. You
          will not be able to see it again.
        </p>
      )}

      {scimData?.scim_url && <p>Your SCIM URL: {scimData.scim_url}</p>}
    </div>
  );
};

export default SCIMSettings;
