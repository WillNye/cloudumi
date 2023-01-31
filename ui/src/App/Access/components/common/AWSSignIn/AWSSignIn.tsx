import Spinner from '@noqdev/cloudscape/spinner';
import { awsLogout, awsSignIn } from 'core/API/auth';
import { extractErrorMessage } from 'core/API/utils';
import { Dispatch, FC, useCallback, useMemo, useState } from 'react';
import { Button } from 'shared/elements/Button';

type AWSSignInProps = {
  role;
  setErrorMessage: Dispatch<string | null>;
};

const AWSSignIn: FC<AWSSignInProps> = ({ role, setErrorMessage }) => {
  const [isLoading, setIsLoading] = useState(false);

  const btnText = useMemo(
    () => (role.inactive_tra ? 'Request Temporary Access' : 'Sign-In'),
    [role]
  );

  const handleAWSSignIn = useCallback(
    async (roleArn: string) => {
      setIsLoading(true);
      try {
        setErrorMessage(null);
        await awsLogout();
        const res = await awsSignIn(roleArn);
        const roleData = res.data;
        if (!roleData) {
          setIsLoading(false);
          return;
        }
        if (roleData.type === 'redirect') {
          window.location.assign(roleData.redirect_url);
        }
        setErrorMessage(roleData.message);
        setIsLoading(false);
      } catch (error) {
        const errorMessage = extractErrorMessage(error);
        setErrorMessage(
          errorMessage || 'Error while generating AWS console URL'
        );
        setIsLoading(false);
      }
    },
    [setErrorMessage]
  );

  const handleOnClick = useCallback(() => {
    if (role.inactive_tra) {
      // TODO support TRA
    } else {
      handleAWSSignIn(role.arn);
    }
  }, [role, handleAWSSignIn]);

  return (
    <Button
      fullWidth
      color={role.inactive_tra ? 'secondary' : 'primary'}
      size="small"
      onClick={handleOnClick}
      disabled={isLoading}
    >
      {isLoading ? <Spinner /> : btnText}
    </Button>
  );
};

export default AWSSignIn;
