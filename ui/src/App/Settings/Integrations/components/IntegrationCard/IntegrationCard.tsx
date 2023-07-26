import { Button } from 'shared/elements/Button';
import { Segment } from 'shared/layout/Segment';
import styles from './IntegrationCard.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { Ref, forwardRef } from 'react';

interface IntegrationCardProps {
  icon: string;
  handleConnect?: () => void;
  title: string;
  description: string;
  link?: string;
  buttonText: string;
  disableBtn?: boolean;
}

const IntegrationCard = forwardRef(
  (
    {
      icon,
      handleConnect,
      title,
      description,
      link,
      buttonText,
      disableBtn
    }: IntegrationCardProps,
    ref: Ref<HTMLButtonElement>
  ) => (
    <Segment>
      <div className={styles.slackIntegration}>
        <img src={icon} alt="Slack Icon" className={styles.icon} />
        <h3 className={styles.title}>{title}</h3>
        <LineBreak />
        <p className={styles.description}>{description}</p>
        <Button
          onClick={handleConnect}
          href={link}
          asAnchor={Boolean(link)}
          className={styles.connectButton}
          color="secondary"
          fullWidth
          disabled={disableBtn}
          ref={ref}
        >
          {buttonText}
        </Button>
      </div>
    </Segment>
  )
);

export default IntegrationCard;
