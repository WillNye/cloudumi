import { Button } from 'shared/elements/Button';
import { Segment } from 'shared/layout/Segment';
import styles from './IntegrationCard.module.css';

interface IntegrationCardProps {
  icon: string;
  handleConnect?: () => void;
  title: string;
  description: string;
}

const IntegrationCard = ({
  icon,
  handleConnect,
  title,
  description
}: IntegrationCardProps) => {
  return (
    <Segment>
      <div className={styles.slackIntegration}>
        <img src={icon} alt="Slack Icon" className={styles.icon} />
        <h3 className={styles.title}>{title}</h3>
        <p className={styles.description}>{description}</p>
        <Button
          onClick={handleConnect}
          className={styles.connectButton}
          color="secondary"
          fullWidth
        >
          Connect
        </Button>
      </div>
    </Segment>
  );
};

export default IntegrationCard;
