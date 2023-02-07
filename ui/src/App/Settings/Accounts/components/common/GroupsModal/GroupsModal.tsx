import { useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';
import { Input } from 'shared/form/Input';
import { Block } from 'shared/layout/Block';
import { Button } from 'shared/elements/Button';
import styles from './GroupsModal.module.css';

const GroupsModal = () => {
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
        header="Group Modal"
        size="medium"
      >
        <div className={styles.container}>
          <form>
            <Block disableLabelPadding label="Group"></Block>
            <Input fullWidth name="group" />
            <Block disableLabelPadding label="Description"></Block>
            <Input fullWidth name="description" />

            <Button>Save</Button>
          </form>
        </div>
      </Dialog>
    </>
  );
};

export default GroupsModal;
