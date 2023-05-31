import { Segment } from 'shared/layout/Segment';
import RequestCard from '../RequestCard';
import awsIcon from '../../../../../assets/integrations/awsIcon.svg';
import gsuiteIcon from '../../../../../assets/integrations/gsuiteIcon.svg';
import azureADIcon from '../../../../../assets/integrations/azureADIcon.svg';
import oktaIcon from '../../../../../assets/integrations/oktaIcon.svg';

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

          <RequestCard title="Okta" icon={oktaIcon} description="Okta" />

          <RequestCard
            title="Azure AD"
            icon={azureADIcon}
            description="Azure Active Directory"
          />

          <RequestCard
            title="Google Workspace"
            icon={gsuiteIcon}
            description="Google Workspace"
          />
        </div>
        <LineBreak size="large" />
        <p className={styles.subText}>
          Can&apos;t find what you&apos;re looking for? Have an administrator{' '}
          <Link to="/settings/integrations">click here</Link> to add a new
          provider
        </p>
      </div>
    </Segment>
  );
};

export default SelectProvider;
