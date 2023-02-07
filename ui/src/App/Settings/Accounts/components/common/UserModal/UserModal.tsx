import { useState } from 'react';
import { Button } from 'shared/elements/Button';
import { Icon } from 'shared/elements/Icon';
import { Input } from 'shared/form/Input';
import { Dialog } from 'shared/layers/Dialog';
import { Block } from 'shared/layout/Block';
import styles from './UserModal.module.css';

const UserModal = () => {
  const [showDialog, setShowDialog] = useState(false);

  return (
    <>
      <div onClick={() => setShowDialog(true)}>
        <Icon name="edit" size="medium" />
      </div>

      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        disablePadding
        header="user Modal"
        size="medium"
      >
        <div className={styles.container}>
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
    </>
  );
};

export default UserModal;
