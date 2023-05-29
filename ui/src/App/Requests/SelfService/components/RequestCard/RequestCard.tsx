import styles from './RequestCard.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { Card } from 'shared/layout/Card';

interface RequestCardProps {
  icon: string;
  onClick?: () => void;
  title: string;
  description: string;
}

const RequestCard = ({
  icon,
  onClick,
  title,
  description
}: RequestCardProps) => {
  return (
    <Card disablePadding>
      <div className={styles.requestCard} onClick={onClick}>
        <img src={icon} alt="Icon" className={styles.icon} />
        <div className={styles.content}>
          <h3 className={styles.title}>{title}</h3>
          <LineBreak size="small" />
          <p className={styles.description}>{description}</p>
        </div>
      </div>
    </Card>
  );
};

export default RequestCard;
