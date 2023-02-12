import Spinner from '@noqdev/cloudscape/spinner';
import { awsSignIn } from 'core/API/auth';
import { extractErrorMessage } from 'core/API/utils';
import { Dispatch, FC, useCallback, useMemo, useState } from 'react';
import { Button } from 'shared/elements/Button';
import { Dialog } from 'shared/layers/Dialog';
import { AWS_SIGN_OUT_URL } from 'App/Access/constants';
import styles from './AWSSignin.module.css';

type AWSSignInProps = {
  role;
  setErrorMessage: Dispatch<string | null>;
};

const AWSSignIn: FC<AWSSignInProps> = ({ role, setErrorMessage }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [showDialog, setShowDialog] = useState(false);

  const btnText = useMemo(
    () => (role.inactive_tra ? 'Request Temporary Access' : 'Sign-In'),
    [role]
  );

  const handleAWSSignIn = useCallback(
    async (roleArn: string) => {
      setIsLoading(true);
      try {
        setErrorMessage(null);
        const res = await awsSignIn(roleArn);
        const roleData = res.data;
        if (!roleData) {
          setIsLoading(false);
          setShowDialog(false);
          return;
        }
        if (roleData.type === 'redirect') {
          window.location.assign(roleData.redirect_url);
        }
        setErrorMessage(roleData.message);
        setIsLoading(false);
        setShowDialog(false);
      } catch (error) {
        const errorMessage = extractErrorMessage(error);
        setErrorMessage(
          errorMessage || 'Error while generating AWS console URL'
        );
        setIsLoading(false);
        setShowDialog(false);
      }
    },
    [setErrorMessage]
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
            onLoad={() => handleAWSSignIn(role.arn)}
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
