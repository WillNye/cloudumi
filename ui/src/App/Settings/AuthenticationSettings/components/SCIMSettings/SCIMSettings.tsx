import React, { useState, useEffect } from 'react';
import axios from 'core/Axios/Axios';
import { Button } from 'shared/elements/Button';
import { toast } from 'react-toastify';

interface ScimSettingsData {
  scim_enabled: boolean;
  scim_url: string;
  scim_secret?: string;
}

const SCIMSettings = ({ isFetching }) => {
  const [scimData, setScimData] = useState<ScimSettingsData | null>(null);

  useEffect(() => {
    const fetchScimSettings = async () => {
      try {
        const response = await axios.get('/api/v4/scim/settings');
        if (response.data.status === 'success') {
          setScimData(response.data.data);
        }
      } catch (error) {
        toast.error('Failed to load SCIM settings');
      }
    };

    fetchScimSettings();
  }, []);

  const handleNewToken = async () => {
    try {
      const response = await axios.post('/api/v4/scim/settings');
      if (response.data.status === 'success') {
        toast.success('New SCIM token generated');
        setScimData(response.data.data);
      } else {
        toast.error(response.data.reason);
      }
    } catch (error) {
      toast.error('Failed to generate new SCIM token');
    }
  };

  const handleDisableScim = async () => {
    try {
      const response = await axios.delete('/api/v4/scim/settings');
      if (response.data.status === 'success') {
        toast.success('SCIM settings disabled');
        setScimData(null);
      }
    } catch (error) {
      toast.error('Failed to disable SCIM settings');
    }
  };

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
          <Button onClick={handleDisableScim}>Disable SCIM</Button>
        </>
      ) : (
        <>
          <Button onClick={handleNewToken}>Generate New SCIM Token</Button>
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
