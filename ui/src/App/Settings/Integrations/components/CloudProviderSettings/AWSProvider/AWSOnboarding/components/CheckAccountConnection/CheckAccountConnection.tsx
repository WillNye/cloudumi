import { useCallback, useEffect } from 'react';
import { getHubAccounts, getSpokeAccounts } from 'core/API/awsConfig';
import { TIME_PER_INTERVAL } from '../../constants';
import AWSMxNetImg from 'assets/vendor/mx-net.svg';
import AWSCacheImg from 'assets/vendor/connect.svg';
import styles from './CheckAccountConnection.module.css';
import { LineBreak } from 'shared/elements/LineBreak';

const CheckAccountConnection = ({
  setIsConnected,
  isHubAccount,
  accountName
}) => {
  const getAccountDetails = useCallback(async () => {
    const getHubSpokeAccount = isHubAccount ? getHubAccounts : getSpokeAccounts;
    const data = await getHubSpokeAccount();
    if (data && data.count) {
      if (isHubAccount) {
        setIsConnected(true);
      } else {
        data.data.forEach(acc => {
          if (acc.account_name === accountName) {
            setIsConnected(true);
          }
        });
      }
    }
  }, [isHubAccount, setIsConnected, accountName]);

  useEffect(() => {
    const interval = setInterval(async () => {
      await getAccountDetails();
    }, TIME_PER_INTERVAL);

    return () => {
      clearInterval(interval);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className={styles.connectingAccount}>
      <div>
        <LineBreak size="large" />

        <div className={styles.loaderActions}>
          <img
            src={AWSMxNetImg}
            className={`${styles.icon} ${styles.rotate}`}
          />
          <div>
            <h3>Onboarding account</h3>
            <p> Waiting for CloudFormation response.</p>
          </div>
        </div>
        <LineBreak size="large" />
        <div className={styles.loaderActions}>
          <img src={AWSCacheImg} className={styles.icon} />
          <div>
            <h3>Caching resources</h3>
            <p>Not started</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CheckAccountConnection;
