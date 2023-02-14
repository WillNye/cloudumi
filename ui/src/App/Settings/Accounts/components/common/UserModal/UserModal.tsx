import { Fragment, useState } from 'react';
import { Button } from 'shared/elements/Button';
import { Icon } from 'shared/elements/Icon';
import { Input } from 'shared/form/Input';
import { Dialog } from 'shared/layers/Dialog';
import { Block } from 'shared/layout/Block';
import styles from './UserModal.module.css';

const UserModal = ({ canEdit }) => {
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
        header="user Modal"
        size="medium"
      >
        <div className={styles.content}>
          <form>
            <Block disableLabelPadding label="First Name"></Block>
            <Input fullWidth name="first_name" />
            <Block disableLabelPadding label="Last Name"></Block>
            <Input fullWidth name="last_name" />
            <Block disableLabelPadding label="Email"></Block>
            <Input fullWidth name="email" />

            <Button>Save</Button>
          </form>
        </div>
      </Dialog>
    </div>
  );
};

export default UserModal;
