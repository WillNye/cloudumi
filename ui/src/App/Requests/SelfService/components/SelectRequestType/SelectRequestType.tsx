import { Segment } from 'shared/layout/Segment';
import RequestCard from '../RequestCard';
import identityIcon from '../../../../../assets/vendor/identity.svg';
import accessIcon from '../../../../../assets/vendor/access.svg';
import permissionsIcon from '../../../../../assets/vendor/permissions.svg';

import styles from './SelectRequestType.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../SelfServiceContext';
import { SELF_SERICE_STEPS } from '../../constants';

const SelectRequestType = () => {
  const {
    actions: { setCurrentStep }
  } = useContext(SelfServiceContext);

  return (
    <Segment>
      <div className={styles.container}>
        <h3>Request Type</h3>
        <LineBreak />
        <p className={styles.subText}>What would you like to do?</p>
        <LineBreak size="large" />
        <div className={styles.cardList}>
          <RequestCard
            title="Create a new Resource"
            icon={identityIcon}
            description="Submit a request to create an AWS IAM Role."
            onClick={() => setCurrentStep(SELF_SERICE_STEPS.COMPLETION_FORM)}
          />

          <RequestCard
            title="Request Access to an existing Resource"
            icon={permissionsIcon}
            description="Submit a request to add IAM permissions to a role."
          />

          <RequestCard
            title="Request Permissions Change"
            icon={accessIcon}
            description="Submit a request to access short-lived AWS IAM role.
            Examples: Update Tags, Add new inline policy"
          />
        </div>
      </div>
    </Segment>
  );
};

export default SelectRequestType;
