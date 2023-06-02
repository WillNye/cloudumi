import Spinner from '@noqdev/cloudscape/spinner';
import { useSearchParams } from 'react-router-dom';
import { awsSignIn } from 'core/API/auth';
import { extractErrorMessage } from 'core/API/utils';
import { Dispatch, FC, useCallback, useMemo, useState } from 'react';
import { Button } from 'shared/elements/Button';
import { Dialog } from 'shared/layers/Dialog';
import { AWS_SIGN_OUT_URL } from 'App/Access/constants';
import { useQuery } from '@tanstack/react-query';
import styles from './AWSSignin.module.css';
import { useEffect } from 'react';
import { useAuth } from 'core/Auth';

type AWSSignInProps = {
  role;
  extraParams?: string;
  showDialogInitially?: boolean;
  setErrorMessage: Dispatch<string | null>;
};

const AWSSignIn: FC<AWSSignInProps> = ({
  role,
  showDialogInitially = false,
  extraParams = '',
  setErrorMessage
}) => {
  const [isLoading, setIsLoading] = useState(showDialogInitially);
  const [showDialog, setShowDialog] = useState(showDialogInitially);
  const [searchParams] = useSearchParams();
  const { user } = useAuth();

  // Region precedence:
  // query param > user-specified settings for role > user generic preferences > org default region
  const queryRegion = searchParams.get('r');
  const OrgDefaultRegion =
    user?.site_config?.access?.aws?.default_region || 'us-east-1';
  const userStoredPreferences = JSON.parse(
    localStorage.getItem('user-preferences') || '{}'
  );
  const userDefaultRegion = userStoredPreferences?.access?.aws?.default_region;
  const effectiveUserDefaultRegion = userDefaultRegion || OrgDefaultRegion;
  const userRoleSpecificSettings = JSON.parse(
    localStorage.getItem('access-settings|' + role.arn) || '{}'
  );
  const regionPreference =
    userRoleSpecificSettings?.region || effectiveUserDefaultRegion;
  const region = queryRegion || regionPreference;
  const servicePreference = userRoleSpecificSettings?.service;

  // Include region and service as extra parameters
  const params = new URLSearchParams(extraParams);
  if (region) {
    params.set('r', region);
  }
  if (servicePreference) {
    params.set(
      'redirect',
      'https://console.aws.amazon.com/' +
        servicePreference +
        '/home?region=' +
        region
    );
  }
  extraParams = params.toString();

  useEffect(() => {
    const warningMessage = searchParams.get('warningMessage');
    if (warningMessage) {
      setErrorMessage(atob(warningMessage));
    }
  }, [searchParams, setErrorMessage]);

  const { refetch: handleAWSSignIn } = useQuery({
    enabled: false,
    queryFn: awsSignIn,
    queryKey: ['awsSignIn', role.arn, extraParams],
    onSuccess: roleData => {
      if (!roleData) {
        setShowDialog(false);
        setIsLoading(false);
        return;
      }
      if (roleData.type === 'redirect') {
        window.location.assign(roleData.redirect_url);
      }
      setErrorMessage(roleData.message);
      setShowDialog(false);
      setIsLoading(false);
    },
    onError: error => {
      const errorMessage = extractErrorMessage(error);
      setErrorMessage(errorMessage || 'Error while generating AWS console URL');
      setShowDialog(false);
      setIsLoading(false);
    }
  });

  const btnText = useMemo(
    () => (role.inactive_tra ? 'Request Temporary Access' : 'Sign-In'),
    [role]
  );

  const handleOnClick = useCallback(() => {
    if (role.inactive_tra) {
      // TODO support TRA
    } else {
      setShowDialog(true);
      setIsLoading(true);
    }
  }, [role]);

  return (
    <>
      <Button
        fullWidth
        color={role.inactive_tra ? 'secondary' : 'primary'}
        size="small"
        onClick={handleOnClick}
        disabled={isLoading}
      >
        {isLoading ? <Spinner /> : btnText}
      </Button>
      <Dialog
        header={<></>}
        size="medium"
        disablePadding
        showDialog={showDialog}
        setShowDialog={setShowDialog}
      >
        <>
          {isLoading && (
            <div className={styles.loader}>
              <Spinner size="large" />
              <div className={styles.loaderText}>
                <p>Just a few seconds...</p>
                <p>Attempting to log into the AWS Console</p>
              </div>
            </div>
          )}
          <iframe
            onLoad={() => handleAWSSignIn()}
            src={AWS_SIGN_OUT_URL}
            style={{
              width: 0,
              height: 0,
              border: 'none'
            }}
            title="Console Sign Out"
          />
        </>
      </Dialog>
    </>
  );
};

export default AWSSignIn;
