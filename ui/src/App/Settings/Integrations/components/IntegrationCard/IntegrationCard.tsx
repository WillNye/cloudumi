import { Button } from 'shared/elements/Button';
import { Segment } from 'shared/layout/Segment';
import styles from './IntegrationCard.module.css';

interface IntegrationCardProps {
  icon: string;
  handleConnect?: () => void;
  title: string;
  description: string;
  link?: string;
  buttonText: string;
  disableBtn?: boolean;
}

const IntegrationCard = ({
  icon,
  handleConnect,
  title,
  // description,
  link,
  buttonText,
  disableBtn
}: IntegrationCardProps) => {
  return (
    <Segment>
      <div className={styles.slackIntegration}>
        <img src={icon} alt="Slack Icon" className={styles.icon} />
        <h3 className={styles.title}>{title}</h3>
        <br />
        {/* <p className={styles.description}>{description}</p> */}
        <Button
          onClick={handleConnect}
          href={link}
          asAnchor={Boolean(link)}
          className={styles.connectButton}
          color="secondary"
          fullWidth
          disabled={disableBtn}
        >
          {buttonText}
        </Button>
      </div>
    </Segment>
  );
};

export default IntegrationCard;
