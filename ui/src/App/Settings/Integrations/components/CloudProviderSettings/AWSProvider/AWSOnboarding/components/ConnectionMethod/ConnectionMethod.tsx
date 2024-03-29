import { Block } from 'shared/layout/Block';
import { Radio } from 'shared/form/Radio';
import styles from '../../AWSOnBoarding.module.css';
import { LineBreak } from 'shared/elements/LineBreak';

const ConnectionMethod = () => {
  return (
    <div className={styles.instructions}>
      <p>
        In order to securely connect to your AWS Environment, Noq requires
        Cross-Account IAM Roles to be created in at least one of your accounts.
        Please read more about this here.
      </p>
      <LineBreak />
      <p>
        If you’re connecting a single account, we recommend that you use the AWS
        Console or AWS CLI, which will create the roles using CloudFormation and
        inform Noq when it is complete.
      </p>
      <LineBreak />
      <p>
        When the roles are accessible, Noq will begin syncing your account data
        automatically.
      </p>
      <LineBreak size="large" />

      <h4>Select the method you would like to connect Noq:</h4>
      <LineBreak />

      <form>
        <div className={styles.radioInput}>
          <Radio defaultChecked />
          <Block disableLabelPadding>AWS Console</Block>
        </div>

        <div className={styles.radioInput}>
          <Radio disabled />
          <Block disableLabelPadding>AWS CLI (Coming Soon)</Block>
        </div>

        <div className={styles.radioInput}>
          <Radio disabled />
          <Block disableLabelPadding>Terraform (Coming Soon)</Block>
        </div>
      </form>
    </div>
  );
};

export default ConnectionMethod;
