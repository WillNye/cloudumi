import { Input } from 'shared/form/Input';
import { Block } from 'shared/layout/Block';
import styles from '../../AWSOnBoarding.module.css';
// import { Icon } from 'shared/elements/Icon';
// import { MODES } from '../../constants';
// import { Radio } from 'shared/form/Radio';
// import { LineBreak } from 'shared/elements/LineBreak';

const ConfigureAccount = ({
  handleAccNameChange,
  accountName
  // selectedMode,
  // handleModeChange
}) => {
  return (
    <div className={styles.configureAccount}>
      <form>
        <Block disableLabelPadding>1. Specify AWS Account Name</Block>
        <Input
          placeholder="Enter AWS Account Name"
          onChange={handleAccNameChange}
          maxLength={50}
          minLength={1}
          value={accountName}
        />
        {/* <LineBreak />
        <Block disableLabelPadding>2. Select Installation Mode:</Block>
        <div className={styles.container}>
          <div className={styles.permissionsBlock}>
            <div className={styles.radioInput}>
              <Radio
                value={MODES.READ_ONLY}
                checked={selectedMode === MODES.READ_ONLY}
                onChange={handleModeChange}
              />
              <Block>Read-Only</Block>
            </div>

            <p>
              Cloud Identities and Resources will not be modified in Read-Only
              mode.
            </p>
            <p>
              This mode only grants Noq privileges to inventory Cloud identities
              and IAM policies. Approved requests will require manual changes to
              apply and remove after expiration.
            </p>
          </div>
          <div className={styles.permissionsBlock}>
            <div className={styles.radioInput}>
              <Radio
                value={MODES.READ_WRTE}
                checked={selectedMode === MODES.READ_WRTE}
                onChange={handleModeChange}
              />
              <Block disableLabelPadding>Read-Write</Block>
              &nbsp;
              <Block color="green">
                <Icon name="star" />
                Recommended
              </Block>
            </div>
            <p>
              Read-write installation <em>can</em> change Cloud identities or
              alter IAM policies to automate request approval or expiration.
            </p>
            <p>
              This mode grants Noq privileges to inventory and change Cloud
              identities and IAM policies. Changes can only occur when users
              make requests using Noq, and they are approved by an
              administrator. Changes will be applied automatically after
              approval and removed automatically after expiration.
            </p>
          </div>
        </div> */}
      </form>
    </div>
  );
};

export default ConfigureAccount;
