import { Fragment, useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';
import { Input } from 'shared/form/Input';
import { Block } from 'shared/layout/Block';
import { Button } from 'shared/elements/Button';
import styles from './GroupsModal.module.css';

const GroupsModal = ({ canEdit }) => {
  const [showDialog, setShowDialog] = useState(false);

  if (!canEdit) {
    return <Fragment />;
  }

  return (
    <div className={styles.container}>
      <div className={styles.btn} onClick={() => setShowDialog(true)}>
        <Icon name="edit" size="medium" />
      </div>

      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        disablePadding
        header="Group Modal"
        size="medium"
      >
        <div className={styles.content}>
          <form>
            <Block disableLabelPadding label="Group"></Block>
            <Input fullWidth name="group" />
            <Block disableLabelPadding label="Description"></Block>
            <Input fullWidth name="description" />

            <Button>Save</Button>
          </form>
        </div>
      </Dialog>
    </div>
  );
};

export default GroupsModal;
