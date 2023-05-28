import { Segment } from 'shared/layout/Segment';
import RequestCard from '../RequestCard';
import awsIcon from '../../../../../assets/integrations/awsIcon.svg';
import gcpIcon from '../../../../../assets/integrations/gcpIcon.svg';
import azureIcon from '../../../../../assets/integrations/azureIcon.svg';

import styles from './SelectProvider.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { Link } from 'react-router-dom';

const SelectProvider = () => {
  return (
    <Segment>
      <div className={styles.container}>
        <h3>Select Provider</h3>
        <LineBreak />
        <p className={styles.subText}>
          Please choose a provider from the list below
        </p>
        <LineBreak size="large" />
        <div className={styles.cardList}>
          <RequestCard
            title="AWS"
            icon={awsIcon}
            description="Amazon web services (AWS)"
          />

          <RequestCard
            title="GCP"
            icon={gcpIcon}
            description="Amazon web services (AWS)"
          />

          <RequestCard
            title="Azure"
            icon={azureIcon}
            description="Amazon web services (AWS)"
          />
        </div>
        <LineBreak size="large" />
        <p className={styles.subText}>
          Can&apos;t find what you&apos;re looking for?{' '}
          <Link to="/settings/integrations">Click here</Link> to add a new
          provider
        </p>
      </div>
    </Segment>
  );
};

export default SelectProvider;
