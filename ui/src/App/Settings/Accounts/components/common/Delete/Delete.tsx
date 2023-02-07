import { useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';
import styles from './Delete.module.css';
import { Button } from 'shared/elements/Button';

const Delete = () => {
  const [showDialog, setShowDialog] = useState(false);

  return (
    <div>
      <div onClick={() => setShowDialog(true)}>
        <Icon name="delete" size="medium" />
      </div>
      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        header="Delete Modal"
        disablePadding
        size="small"
      >
        <div className={styles.container}>
          <div>Are you sure you want to delete?</div>
          <div>
            <Button color="error">Delete</Button>
            <Button color="secondary" variant="outline">
              Cancel
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
};

export default Delete;
