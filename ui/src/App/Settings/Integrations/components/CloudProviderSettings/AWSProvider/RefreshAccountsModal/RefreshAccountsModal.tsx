import { Button } from 'shared/elements/Button';
import { LineBreak } from 'shared/elements/LineBreak';
import { Dialog } from 'shared/layers/Dialog';

const RefreshAccountsModal = ({ show, onClose }) => {
  return (
    <Dialog
      header="Refreshing Accounts"
      size="medium"
      setShowDialog={onClose}
      showDialog={show}
    >
      <div>
        We are refreshing accounts within your AWS organization(s). If you do
        not see the expected accounts in a few minutes, please confirm that
        IAMbic is configured properly for your organization.
        <LineBreak />
        First, confirm that your `iambic-config.yaml` file has the expected
        accounts specified in them.
        <LineBreak />
        Second, ensure that your NoqSpokeRole role definition is deployed to all
        accounts. If it is not, please add the following to your NoqSpokeRole
        IAMbic template:
        <LineBreak />
        <pre>
          <code>
            {`included_accounts:
         - "*"`}
          </code>
        </pre>
        <div style={{ marginTop: '1rem', textAlign: 'center' }}>
          <Button onClick={onClose}>OK</Button>
        </div>
      </div>
    </Dialog>
  );
};

export default RefreshAccountsModal;
