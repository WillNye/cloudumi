import { Fragment, useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';
import { Button } from 'shared/elements/Button';
import styles from './Delete.module.css';

const Delete = ({ canEdit }) => {
  const [showDialog, setShowDialog] = useState(false);

  if (!canEdit) {
    return <Fragment />;
  }

  return (
    <div className={styles.container}>
      <div className={styles.btn} onClick={() => setShowDialog(true)}>
        <Icon name="delete" size="medium" />
      </div>
      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        header="Delete Modal"
        disablePadding
        size="small"
      >
        <div className={styles.content}>
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
