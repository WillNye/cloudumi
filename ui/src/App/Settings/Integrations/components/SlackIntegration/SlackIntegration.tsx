import styles from './SlackIntegration.module.css';
import slackIcon from './slackIcon.svg';
import { Segment } from 'shared/layout/Segment';
import { Button } from 'shared/elements/Button';

const SlackIntegration = () => {
  const handleConnect = () => {
    // connect to Slack
  };

  return (
    <Segment>
      <div className={styles.slackIntegration}>
        <img src={slackIcon} alt="Slack Icon" className={styles.icon} />
        <h3 className={styles.title}>Connect to Slack</h3>
        <p className={styles.description}>
          Connect your Slack account to access team messaging and notifications.
        </p>
        <Button onClick={handleConnect} className={styles.connectButton}>
          Connect
        </Button>
      </div>
    </Segment>
  );
};

export default SlackIntegration;
