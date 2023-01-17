import { useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';

const RoleCredentialSummary = () => {
  const [showDialog, setShowDialog] = useState(false);

  return (
    <>
      <div onClick={() => setShowDialog(!showDialog)}>
        <Icon name="break-glass" size="large" color="secondary" />
      </div>
      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        size="medium"
      >
        <pre>
          Noq CLI To retrieve AWS credentials on demand noq credential_process
          -g prod/prod_admin noq serve prod/prod_admin noq file prod/prod_admin
          -p prod/prod_admin noq export prod/prod_admin
        </pre>
        <pre>
          Noq CLI To retrieve AWS credentials on demand noq credential_process
          -g prod/prod_admin noq serve prod/prod_admin noq file prod/prod_admin
          -p prod/prod_admin noq export prod/prod_admin
        </pre>
        <br />
        <pre>
          Noq CLI To retrieve AWS credentials on demand noq credential_process
          -g prod/prod_admin noq serve prod/prod_admin noq file prod/prod_admin
          -p prod/prod_admin noq export prod/prod_admin
        </pre>
        <br />
        <pre>
          Noq CLI To retrieve AWS credentials on demand noq credential_process
          -g prod/prod_admin noq serve prod/prod_admin noq file prod/prod_admin
          -p prod/prod_admin noq export prod/prod_admin
        </pre>
        <br />
        <pre>
          Noq CLI To retrieve AWS credentials on demand noq credential_process
          -g prod/prod_admin noq serve prod/prod_admin noq file prod/prod_admin
          -p prod/prod_admin noq export prod/prod_admin
        </pre>
      </Dialog>
    </>
  );
};

export default RoleCredentialSummary;
