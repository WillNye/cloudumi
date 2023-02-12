import { AWS_SIGN_OUT_URL } from 'App/Access/constants';
import { awsRoleLogin } from 'core/API/roles';
import { getLocalStorageSettings } from 'core/utils/localstorage';
import { useCallback, useState } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { Spinner } from 'shared/elements/Spinner';
import styles from './AWSLogin.module.css';

const AWSLogin = ({ handleAWSSignIn, isLoading }) => {
  //   const { search } = useLocation();
  //   const { roleQuery } = useParams();
  //   const [errorMessage, setErrorMessage] = useState('text');
  //   const userDefaultAwsRegionSetting = getLocalStorageSettings(
  //     'defaultAwsConsoleRegion'
  //   );

  //   const handleSignIn = useCallback(async () => {
  //     let extraArgs = '';
  //     if (userDefaultAwsRegionSetting && !search) {
  //       extraArgs = '?r=' + userDefaultAwsRegionSetting;
  //     }
  //     const roleDataRes = await awsRoleLogin({ roleQuery, search, extraArgs });
  //     const roleData = roleDataRes.data;

  //     if (!roleData) {
  //       return;
  //     }

  //     if (roleData.type === 'redirect') {
  //       window.location.assign(roleData.redirect_url);
  //     }

  //     setErrorMessage(roleData.message);
  //   }, [roleQuery, search, userDefaultAwsRegionSetting]);

  return (
    <div className={styles.container}>
      {/* {errorMessage ? (
        <div>
          <Notification
            fullWidth
            showCloseIcon={false}
            type={NotificationType.ERROR}
            header="Oops! there was a problem"
          >
            <p>{errorMessage}</p>
          </Notification>
        </div>
      ) : (

      )} */}
    </div>
  );
};

export default AWSLogin;
